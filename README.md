# cnc_sms_v2.py
@Tratackoquat

## Công cụ kiểm tra tài khoản Facebook

Script `facebook_account_checker.py` giúp bạn kiểm tra nhanh một hoặc nhiều UID xem tài khoản còn hoạt động hay đã bị vô hiệu hóa.

- Yêu cầu Python 3.8+. Có thể sử dụng thêm Graph API access token (tùy chọn) để tăng độ chính xác.
- Nếu không có token, script sẽ kiểm tra dựa trên trang web công khai của Facebook.
- Hỗ trợ nhập UID trực tiếp, qua danh sách hoặc file.

### Ví dụ sử dụng

```bash
# Kiểm tra một UID duy nhất
python facebook_account_checker.py --uid 1000123456789

# Kiểm tra nhiều UID và xuất JSON
python facebook_account_checker.py --uids 10001 10002 10003 --json

# Dùng access token nếu có
python facebook_account_checker.py --uid 1000123456789 --access-token <TOKEN>
```

Script sẽ phân loại kết quả theo các trạng thái: `ALIVE`, `NOT_FOUND`, `LOGIN_REQUIRED`, `PERMISSION_DENIED`, `INVALID_TOKEN`, hoặc `UNKNOWN`. 
