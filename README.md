# cnc_sms_v2.py
@Tratackoquat

## Công cụ kiểm tra livestream Facebook

Script `facebook_live_checker.py` cho phép bạn kiểm tra nhanh xem một Trang hoặc một video cụ thể có đang phát livestream trên Facebook hay không.

- Yêu cầu Python 3.8+ và một Graph API access token hợp lệ.
- Cài đặt biến môi trường `FACEBOOK_ACCESS_TOKEN` hoặc truyền token qua dòng lệnh.

### Ví dụ sử dụng

```bash
python facebook_live_checker.py --page-id <PAGE_ID>
python facebook_live_checker.py --video-id <VIDEO_ID> --access-token <TOKEN>
```

Script sẽ trả về thông tin chi tiết về các livestream đang hoạt động hoặc trạng thái của video được yêu cầu. 
