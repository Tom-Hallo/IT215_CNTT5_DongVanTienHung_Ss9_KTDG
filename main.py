from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any

flights_db = [
    {"id": 1, "flight_number": "VN-213", "destination": "Da Nang", "available_seats": 45, "status": "scheduled", "created_at": "2026-07-01T06:00:00Z"},
    {"id": 2, "flight_number": "VJ-122", "destination": "Phu Quoc", "available_seats": 12, "status": "scheduled", "created_at": "2026-07-01T07:30:00Z"}
]

app = FastAPI()

class FlightInformation(BaseModel):
    flight_number: str = Field(min_length=5, max_length=10, examples=["QH-244"])
    destination: str = Field(min_length=1, examples=["Ha Noi"])
    available_seats: int = Field(ge=1, examples=[180])

class APIResponse(BaseModel):
    statusCode: int      
    message: str
    data: Any | None = None
    error: str | None = None
    timestamp: str
    path: str

def response_handler(code: int, message: str, data: Any = None, error: str = None, path: str = "") -> dict:
    return {
        "statusCode": code,
        "message": message,
        "data": data,
        "error": error,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "path": path
    }

@app.exception_handler(HTTPException)
def custom_http_exception_handler(request: Request, exc: HTTPException):
    error_msg = None
    
    if exc.status_code == 400:
        error_msg = "ERR-AIR-01: Flight number conflict in current active schedule database."
    elif exc.status_code == 404:
        error_msg = "ERR-AIR-02: Target flight ID is missing from system scope."
    else:
        error_msg = str(exc.detail)

    return JSONResponse(
        status_code=exc.status_code,
        content=response_handler(
            code=exc.status_code,
            message=exc.detail,
            data=None,
            error=error_msg,
            path=request.url.path
        )
    )


@app.get("/flights", tags=["Flights"], response_model=APIResponse)
def show_flights(request: Request, status: str | None = None):
    if status:
        filtered_flights = [f for f in flights_db if f["status"].lower() == status.lower()]
    else:
        filtered_flights = flights_db

    return response_handler(
        code=200,
        message="Lấy danh sách chuyến bay thành công!",
        data=filtered_flights,
        path=request.url.path
    )

@app.post("/flights", tags=["Flights"], response_model=APIResponse, status_code=status.HTTP_201_CREATED)
def add_new_flight(request: Request, flight_request: FlightInformation):
    is_duplicate = any(f["flight_number"].lower() == flight_request.flight_number.lower() for f in flights_db)
    if is_duplicate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Lỗi: Số hiệu chuyến bay này đã tồn tại trên hệ thống điều hành!"
        )

    next_id = max([f["id"] for f in flights_db], default=0) + 1

    new_flight = {
        "id": next_id,
        "flight_number": flight_request.flight_number.upper(), # Chuẩn hóa viết hoa mã bay
        "destination": flight_request.destination,
        "available_seats": flight_request.available_seats,
        "status": "scheduled",
        "created_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    }

    flights_db.append(new_flight)

    return response_handler(
        code=201,
        message="Khởi tạo chuyến bay mới thành công!",
        data=new_flight,
        path=request.url.path
    )

@app.delete("/flights/{flight_id}", tags=["Flights"], response_model=APIResponse)
def delete_flight(flight_id: int, request: Request):
    found_flight = next((flight for flight in flights_db if flight["id"] == flight_id), None)

    if not found_flight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Lỗi: Không tìm thấy mã chuyến bay yêu cầu để hủy!"
        )

    flights_db.remove(found_flight)
    
    return response_handler(
        code=200,
        message="Hủy chuyến bay thành công!",
        data=None,
        error=None,
        path=request.url.path
    )