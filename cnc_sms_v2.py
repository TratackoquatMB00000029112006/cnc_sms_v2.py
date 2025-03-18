from pystyle import Colorate, Colors
import os
import threading
import socketserver
import sqlite3
import datetime
import requests
from colorama import Fore, init
import logging
import time

# Thiết lập logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Khởi tạo colorama
init(convert=True)

# Quản lý trạng thái spam
active_spams = {}
MAX_CONCURRENT_SPAMS = 1
spam_lock = threading.Lock()

# Biến kiểm soát trạng thái bảo trì
MAINTENANCE_MODE = False  # Đặt True để bật chế độ bảo trì, False để tắt

#Ip
host = '0.0.0.0'

#Port run
port = 5555

# --- Giao diện (UI) ---
class UI:
    CLEAR_SCREEN = "\x1b[2J\x1b[H"

    @staticmethod
    def login_banner():
        banner = [
            "         🌙 MOON SPAM - LOGIN 🌙         ",
            "                _.u[[/;:,.         .odMMMMMM' ",
            "              .o888UU[[[/;:-.  .o@P^    MMM^  ",
            "             oN88888UU[[[/;::-.        dP^    ",
            "            dNMMNN888UU[[[/;:--.   .o@P^      ",
            "           ,MMMMMMN888UU[[/;::-. o@^          ",
            "           NNMMMNN888UU[[[/~.o@P^             ",
            "           888888888UU[[[/o@^-..              ",
            "          oI8888UU[[[/o@P^:--..               ",
            "       .@^  YUU[[[/o@^;::---..                ",
            "     oMP     ^/o@P^;:::---..                  ",
            "  .dMMM    .o@^ ^;::---...                    ",
            " dMMMMMMM@^`       `^^^^                      ",
            "YMMMUP^                                       ",
        ]
        return "\r\n".join(Colorate.Horizontal(Colors.purple_to_blue, line) for line in banner) + "\r\n"

    @staticmethod
    def main_banner():
        banner = [
            "         🌙 MOON SPAM - SPAMMER 🌙              ",
            "                [Beta v1.0]                      ",
            "    █████  █████  █████  ███       ███           ",
            "    █      █   █  █   █  ██ █     █ ██           ",
            "    █████  █████  █████  ██  █   █  ██           ",
            "        █  █      █   █  ██   █ █   ██           ",
            "    █████  █      █   █  ██    █    ██           ",
            "               @ZzTLINHzZ                        ",
            "             READY TO SPAM                       ",
        ]
        return "\r\n".join(Colorate.Horizontal(Colors.red_to_purple, line) for line in banner) + "\r\n"

    @staticmethod
    def help_menu():
        banner = [
            "                     🌙 MOON SPAM - HELP 🌙                     ",
            "╔════════════╦═══════════════════════════════════════════════╗",
            "║ COMMAND    ║ DESCRIPTION                                   ║",
            "╠════════════╬═══════════════════════════════════════════════╣",
            "║ ? / HELP   ║ Show this menu                                ║",
            "║ CLEAR / CLS║ Clear screen                                  ║",
            "║ METHODS    ║ Show spam methods                             ║",
            "║ ABOUT      ║ Admin info                                    ║",
            "║ EXIT       ║ Exit session                                  ║",
            "║ PASSWORD   ║ Change password: <old_pass> <new_pass>        ║",
            "║ CREATE     ║ Create user (admin): <user> <pass> <lev> <end>║",
            "║ DELETE     ║ Delete user (admin): <username>               ║",
            "║ SETTIME    ║ Set expiration (admin): <user> <date_end>     ║",
            "║ SHOW       ║ Show all users (admin)                        ║",
            "╚════════════╩═══════════════════════════════════════════════╝",
        ]
        return "\r\n".join(Colorate.Horizontal(Colors.purple_to_blue, line) for line in banner) + "\r\n"

    @staticmethod
    def methods():
        banner = [
            "      🌙 MOON SPAM - METHODS 🌙      ",
            "[ Usage: .<method> <phone> <time> ]",
            "- FREE      : FREE Spam [Online] ⬤  ",
            "- SMS      : SMS Spam [Online] ⬤  ",
            "- CALL     : Call Spam [Online] ⬤ ",
        ]
        return "\r\n".join(Colorate.Horizontal(Colors.purple_to_blue, line) for line in banner) + "\r\n"

    @staticmethod
    def about():
        banner = [
            "          🌙 MOON SPAM - ABOUT 🌙         ",
            "Developed by: @ZzTLINHzZ (Telegram)  ",
            "Purpose: SMS & Call testing service      ",
            "Version: Beta 1.0                        ",
            "Contact: Telegram @ZzTLINHzZ        ",
            "Last Update: February 25, 2025           ",
        ]
        return "\r\n".join(Colorate.Horizontal(Colors.purple_to_blue, line) for line in banner) + "\r\n"

    @staticmethod
    def spam_confirmation(phone, username, method, time):
        banner = [
            "      🌙 MOON SPAM - LAUNCHED 🌙     ",
            "╔════════════════════════════════════╗",
            f"║ Method: {method:<20}       ║",
            f"║ Target: {phone:<20}       ║",
            f"║ User:   {username:<20}       ║",
            f"║ Time:   {time:<20} sec   ║",
            "╚════════════════════════════════════╝",
            "           Nguyễn Văn Trọng!          ",
        ]
        return "\r\n".join(Colorate.Horizontal(Colors.purple_to_blue, line) for line in banner) + "\r\n"

# --- Giao diện bảo trì ---
class MaintenanceUI:
    @staticmethod
    def maintenance_banner():
        banner = [
            "         🌙 MOON SPAM - MAINTENANCE 🌙         ",
            "                                               ",
            "    ⚠ HỆ THỐNG ĐANG BẢO TRÌ, VUI LÒNG ĐỢI! ⚠  ",
            "                                               ",
            "  Chúng tôi đang nâng cấp hệ thống để phục vụ  ",
            "       bạn tốt hơn. Vui lòng quay lại sau!     ",
            "                                               ",
            "          Liên hệ: Telegram @ZzTLINHzZ         ",
            "                                               ",
        ]
        return "\r\n".join(Colorate.Horizontal(Colors.red_to_yellow, line) for line in banner)

# --- Logic xử lý lệnh ---
class CommandHandler:
    API_ENDPOINTS = {
        'FREE': 'http://127.0.0.1:8080/api?key=admin&phone={phone}&time={time}&methods=FREE',
        'SMS': 'http://127.0.0.1:8080/api?key=admin&phone={phone}&time={time}&methods=SMS',
        'CALL': 'http://127.0.0.1:8080/api?key=admin&phone={phone}&time={time}&methods=CALL'
    }
    TITLE_ESCAPE = "\033]0; MOON SPAM - {method} - {phone} - Time: {time} sec\007"
    TITLE_DEFAULT = "\033]0; MOON SPAM - Ready\007"

    def __init__(self, username, wfile):
        self.username = username
        self.wfile = wfile
        self.db = sqlite3.connect('data.db', check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.current_prompt_row = 10
        self.commands = {
            '?': self.show_help,
            'HELP': self.show_help,
            'CLEAR': self.clear_screen,
            'CLS': self.clear_screen,
            'METHODS': self.show_methods,
            'ABOUT': self.show_about,
            'EXIT': self.exit_session,
            '.SMS': self.launch_spam,
            '.CALL': self.launch_spam,
            '.FREE': self.launch_spam,
            'CREATE': self.create_user,
            'DELETE': self.delete_user,
            'SETTIME': self.set_time,
            'SHOW': self.show_users,
            'PASSWORD': self.change_password
        }
        self._sync_active_spams()

    def send(self, data, escape=True, reset=True):
        try:
            if reset:
                data += Fore.RESET + "\033[49m"
            if escape:
                data += '\r\n'
            if not self.wfile.closed:
                self.wfile.write(data.encode('utf-8'))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionError, OSError):
            logging.error("Connection to client lost")
            raise SystemExit

    def is_admin(self):
        try:
            cursor = self.db.cursor()
            cursor.execute("SELECT lever FROM users WHERE username = ?", (self.username,))
            result = cursor.fetchone()
            return result and result[0] == "admin"
        except sqlite3.Error as e:
            self.send(Fore.RED + f"Database error: {str(e)}")
            return False

    def show_help(self, args):
        self.send(UI.CLEAR_SCREEN, escape=False)
        self.send(UI.help_menu(), escape=False)
        self.current_prompt_row = 16
        self._draw_prompt()

    def clear_screen(self, args):
        self.send(UI.CLEAR_SCREEN, escape=False)
        self.send(UI.main_banner(), escape=False)
        self.current_prompt_row = 10
        self._draw_prompt()

    def show_methods(self, args):
        self.send(UI.CLEAR_SCREEN, escape=False)
        self.send(UI.methods(), escape=False)
        self.current_prompt_row = 6
        self._draw_prompt()

    def show_about(self, args):
        self.send(UI.CLEAR_SCREEN, escape=False)
        self.send(UI.about(), escape=False)
        self.current_prompt_row = 7
        self._draw_prompt()

    def exit_session(self, args):
        self.send(Fore.GREEN + "Goodbye, see you again!", True)
        raise SystemExit

    def change_password(self, args):
        self.send(UI.CLEAR_SCREEN, escape=False)
        if len(args) < 3:
            self.send(Fore.YELLOW + "Usage: PASSWORD <old_password> <new_password>", escape=False)
            self.current_prompt_row = 2
            self._draw_prompt()
            return
        
        old_password = args[1]
        new_password = args[2]

        try:
            cursor = self.db.cursor()
            cursor.execute("SELECT password FROM users WHERE username = ?", (self.username,))
            result = cursor.fetchone()
            
            if not result:
                self.send(Fore.RED + "User not found!", escape=False)
                self.current_prompt_row = 2
                self._draw_prompt()
                return
            if result[0] != old_password:
                self.send(Fore.RED + "Incorrect old password!", escape=False)
                self.current_prompt_row = 2
                self._draw_prompt()
                return
            
            cursor.execute("UPDATE users SET password = ? WHERE username = ?", (new_password, self.username))
            self.db.commit()
            self.send(Fore.GREEN + "Password changed successfully!", escape=False)
        except sqlite3.Error as e:
            self.send(Fore.RED + f"Database error: {str(e)}", escape=False)
        
        self.current_prompt_row = 2  # Đặt lại vị trí sau khi hoàn thành
        self._draw_prompt()

    def launch_spam(self, args):
        self.send(UI.CLEAR_SCREEN, escape=False)
        try:
            method = args[0].upper()[1:]
            if len(args) < 3:
                self.send(Fore.YELLOW + f"Usage: .{method.lower()} <phone> <time>", escape=False)
                self.current_prompt_row = 2
                self._draw_prompt()
                return
            phone, time = args[1], args[2]

            if not (self.validate_phone(phone) and self.validate_time(time)):
                self.send(Fore.RED + "Invalid phone or time! (Phone: 10-11 digits, Time: 10-120)", escape=False)
                self.current_prompt_row = 2
                self._draw_prompt()
                return
            time_int = int(time)
            if time_int > 120:
                self.send(Fore.RED + "Time must not exceed 120 seconds!", escape=False)
                self.current_prompt_row = 2
                self._draw_prompt()
                return

            with spam_lock:
                self._clean_expired_spams()
                if self.is_phone_locked(phone):
                    remaining_time = self.get_remaining_time(phone)
                    if remaining_time > 0:
                        self.send(Fore.RED + f"Phone {phone} is still locked for {remaining_time} seconds!", escape=False)
                        self.current_prompt_row = 2
                        self._draw_prompt()
                        cursor = self.db.cursor()
                        cursor.execute("SELECT method FROM spam_states WHERE phone = ?", (phone,))
                        result = cursor.fetchone()
                        if result:
                            locked_method = result[0]
                            threading.Thread(target=self._manage_spam, args=(phone, remaining_time, locked_method), daemon=True).start()
                        return
                    active_spams.pop(phone, None)
                    self.clear_spam_state(phone)
                
                active_count = self.get_active_spam_count()
                if active_count >= MAX_CONCURRENT_SPAMS:
                    self.send(Fore.RED + f"Maximum {MAX_CONCURRENT_SPAMS} concurrent spams reached!", escape=False)
                    self.current_prompt_row = 2
                    self._draw_prompt()
                    return

                self.save_spam_state(phone, method, time_int)
                active_spams[phone] = True

            url = self.API_ENDPOINTS[method].format(phone=phone, time=time)
            try:
                response = requests.get(url, timeout=5)
                response.raise_for_status()
                self.send(UI.spam_confirmation(phone, self.username, method, time), escape=False)
                self.current_prompt_row = 9
                self._draw_prompt()
                threading.Thread(target=self._manage_spam, args=(phone, time_int, method), daemon=True).start()
            except requests.RequestException as e:
                self.send(Fore.RED + f"Spam failed: {str(e)}", escape=False)
                self.current_prompt_row = 2
                self._draw_prompt()
                with spam_lock:
                    active_spams.pop(phone, None)
                    self.clear_spam_state(phone)
        except Exception as e:
            self.send(Fore.RED + f"Error in spam launch: {str(e)}", escape=False)
            self.current_prompt_row = 2
            self._draw_prompt()
            with spam_lock:
                active_spams.pop(phone, None)
                self.clear_spam_state(phone)

    def _manage_spam(self, phone, duration, method):
        try:
            start_time = time.time()
            end_time = start_time + duration

            while time.time() < end_time:
                remaining = int(end_time - time.time())
                if remaining < 0:
                    break
                if not self.wfile.closed:
                    title = self.TITLE_ESCAPE.format(method=method, phone=phone, time=remaining)
                    self.send(title, escape=False, reset=False)
                time.sleep(1)

            if not self.wfile.closed:
                self.send(self.TITLE_DEFAULT, escape=False, reset=False)
        except (BrokenPipeError, ConnectionError, OSError):
            logging.info(f"Client disconnected during spam for {phone}")
        except Exception as e:
            logging.error(f"Error in manage_spam for {phone}: {str(e)}")
        finally:
            with spam_lock:
                active_spams.pop(phone, None)
                self.clear_spam_state(phone)

    def save_spam_state(self, phone, method, duration):
        try:
            cursor = self.db.cursor()
            start_time = datetime.datetime.now()
            end_time = start_time + datetime.timedelta(seconds=duration)
            cursor.execute("""
                INSERT OR REPLACE INTO spam_states (phone, method, start_time, end_time)
                VALUES (?, ?, ?, ?)
            """, (phone, method, start_time.isoformat(), end_time.isoformat()))
            self.db.commit()
        except sqlite3.Error as e:
            self.send(Fore.RED + f"Database error: {str(e)}")

    def clear_spam_state(self, phone):
        try:
            cursor = self.db.cursor()
            cursor.execute("DELETE FROM spam_states WHERE phone = ?", (phone,))
            self.db.commit()
        except sqlite3.Error as e:
            self.send(Fore.RED + f"Database error: {str(e)}")

    def is_phone_locked(self, phone):
        try:
            cursor = self.db.cursor()
            cursor.execute("SELECT end_time FROM spam_states WHERE phone = ?", (phone,))
            result = cursor.fetchone()
            if result:
                end_time = datetime.datetime.fromisoformat(result[0])
                return end_time > datetime.datetime.now()
            return False
        except (sqlite3.Error, ValueError) as e:
            self.send(Fore.RED + f"Database or time parsing error: {str(e)}")
            return False

    def get_remaining_time(self, phone):
        try:
            cursor = self.db.cursor()
            cursor.execute("SELECT end_time FROM spam_states WHERE phone = ?", (phone,))
            result = cursor.fetchone()
            if result:
                end_time = datetime.datetime.fromisoformat(result[0])
                remaining = (end_time - datetime.datetime.now()).total_seconds()
                return max(0, int(remaining))
            return 0
        except (sqlite3.Error, ValueError) as e:
            self.send(Fore.RED + f"Database or time parsing error: {str(e)}")
            return 0

    def get_active_spam_count(self):
        try:
            cursor = self.db.cursor()
            cursor.execute("SELECT COUNT(*) FROM spam_states WHERE end_time > ?", (datetime.datetime.now().isoformat(),))
            result = cursor.fetchone()
            return result[0] if result else 0
        except sqlite3.Error as e:
            self.send(Fore.RED + f"Database error: {str(e)}")
            return 0

    def _clean_expired_spams(self):
        try:
            cursor = self.db.cursor()
            cursor.execute("DELETE FROM spam_states WHERE end_time <= ?", (datetime.datetime.now().isoformat(),))
            self.db.commit()
        except sqlite3.Error as e:
            self.send(Fore.RED + f"Database error: {str(e)}")

    def _sync_active_spams(self):
        try:
            cursor = self.db.cursor()
            cursor.execute("SELECT phone, method, end_time FROM spam_states")
            active_spams_found = False
            for row in cursor.fetchall():
                phone, method, end_time_str = row
                try:
                    end_time = datetime.datetime.fromisoformat(end_time_str)
                    if end_time > datetime.datetime.now():
                        remaining = (end_time - datetime.datetime.now()).total_seconds()
                        if remaining > 0:
                            with spam_lock:
                                if phone not in active_spams:
                                    active_spams[phone] = True
                                    active_spams_found = True
                                    if not self.wfile.closed:
                                        title = self.TITLE_ESCAPE.format(method=method, phone=phone, time=int(remaining))
                                        self.send(title, escape=False, reset=False)
                                    threading.Thread(target=self._manage_spam, args=(phone, int(remaining), method), daemon=True).start()
                    else:
                        self.clear_spam_state(phone)
                except ValueError as e:
                    self.send(Fore.RED + f"Invalid time format in spam_states: {end_time_str}")
                    logging.error(f"Invalid time format: {str(e)}")
                    self.clear_spam_state(phone)
            if not active_spams_found and not self.wfile.closed:
                self.send(self.TITLE_DEFAULT, escape=False, reset=False)
        except sqlite3.Error as e:
            self.send(Fore.RED + f"Database error: {str(e)}")
            if not self.wfile.closed:
                self.send(self.TITLE_DEFAULT, escape=False, reset=False)

    def create_user(self, args):
        self.send(UI.CLEAR_SCREEN, escape=False)
        if not self.is_admin():
            self.send(Fore.RED + "Permission denied. Admin only!", escape=False)
            self.current_prompt_row = 2
            self._draw_prompt()
            return
        if len(args) < 5:
            self.send(Fore.YELLOW + "Usage: CREATE <username> <password> <lever> <date_end>", escape=False)
            self.current_prompt_row = 2
            self._draw_prompt()
            return
        username, password, lever, date_end = args[1], args[2], args[3], args[4]
        try:
            cursor = self.db.cursor()
            cursor.execute("INSERT INTO users (username, password, lever, date_end) VALUES (?, ?, ?, ?)",
                           (username, password, lever, date_end))
            self.db.commit()
            self.send(Fore.GREEN + "User created", escape=False)
        except sqlite3.IntegrityError:
            self.send(Fore.RED + f"Username '{username}' already exists!", escape=False)
        self.current_prompt_row = 2
        self._draw_prompt()

    def delete_user(self, args):
        self.send(UI.CLEAR_SCREEN, escape=False)
        if not self.is_admin():
            self.send(Fore.RED + "Permission denied. Admin only!", escape=False)
            self.current_prompt_row = 2
            self._draw_prompt()
            return
        if len(args) < 2:
            self.send(Fore.YELLOW + "Usage: DELETE <username>", escape=False)
            self.current_prompt_row = 2
            self._draw_prompt()
            return
        username = args[1]
        try:
            cursor = self.db.cursor()
            cursor.execute("DELETE FROM users WHERE username = ?", (username,))
            self.db.commit()
            self.send(Fore.GREEN + f"User {username} deleted", escape=False)
        except sqlite3.Error as e:
            self.send(Fore.RED + f"Database error: {str(e)}", escape=False)
        self.current_prompt_row = 2
        self._draw_prompt()

    def set_time(self, args):
        self.send(UI.CLEAR_SCREEN, escape=False)
        if not self.is_admin():
            self.send(Fore.RED + "Permission denied. Admin only!", escape=False)
            self.current_prompt_row = 2
            self._draw_prompt()
            return
        if len(args) < 3:
            self.send(Fore.YELLOW + "Usage: SETTIME <username> <date_end>", escape=False)
            self.current_prompt_row = 2
            self._draw_prompt()
            return
        username, date_end = args[1], args[2]
        try:
            cursor = self.db.cursor()
            cursor.execute("UPDATE users SET date_end = ? WHERE username = ?", (date_end, username))
            self.db.commit()
            self.send(Fore.GREEN + f"User {username} expiration set to: {date_end}", escape=False)
        except sqlite3.Error as e:
            self.send(Fore.RED + f"Database error: {str(e)}", escape=False)
        self.current_prompt_row = 2
        self._draw_prompt()

    def show_users(self, args):
        self.send(UI.CLEAR_SCREEN, escape=False)
        if not self.is_admin():
            self.send(Fore.RED + "Permission denied. Admin only!", escape=False)
            self.current_prompt_row = 2
            self._draw_prompt()
            return
        try:
            cursor = self.db.cursor()
            cursor.execute("SELECT * FROM users")
            users = cursor.fetchall()
            self.send(Fore.CYAN + "ID    | USER                  | LEVER   | DATE_END         ", escape=True)
            for user in users:
                self.send(Fore.WHITE + f"{str(user[0]):<5} | {user[1]:<21} | {user[3]:<7} | {user[4]}", escape=True)
            self.current_prompt_row = len(users) + 2
        except sqlite3.Error as e:
            self.send(Fore.RED + f"Database error: {str(e)}", escape=False)
        self._draw_prompt()

    def validate_phone(self, phone):
        return phone.isdigit() and 10 <= len(phone) <= 11

    def validate_time(self, time):
        return time.isdigit() and 10 <= int(time) <= 120

    def _draw_prompt(self):
        prompt = f"\033[45m{Fore.WHITE} [{self.username}@MOON-SPAM] {Fore.RESET}>\033[49m "
        try:
            if not self.wfile.closed:
                self.wfile.write(f"\033[{self.current_prompt_row};1H".encode('utf-8'))
                self.wfile.write(f"\033[K".encode('utf-8'))  # Xóa dòng cũ
                self.wfile.write(prompt.encode('utf-8'))
                self.wfile.write(f"\033[{len(self.username) + 16}G".encode('utf-8'))  # Điều chỉnh con trỏ
                self.wfile.flush()
        except (BrokenPipeError, ConnectionError, OSError):
            raise SystemExit

    def execute(self, command_line):
        args = command_line.strip().split()
        if not args:
            self._draw_prompt()
            return
        cmd = args[0].upper()
        if cmd in self.commands:
            self.commands[cmd](args)
        else:
            self.send(UI.CLEAR_SCREEN, escape=False)
            self.send(Fore.YELLOW + f"Unknown command: '{cmd}'. Type '?' or 'HELP' for help.", escape=False)
            self.current_prompt_row = 2
            self._draw_prompt()

# --- Telnet Handler ---
class TelnetHandler(socketserver.StreamRequestHandler):
    def handle(self):
        try:
            self.wfile.write(UI.login_banner().encode('utf-8'))
            self.wfile.flush()

            username = self._get_login_input("Username: ")
            if not username:
                self.send(Fore.YELLOW + "Username cannot be empty!")
                return

            password = self._get_login_input("Password: ")
            if not password:
                self.send(Fore.YELLOW + "Password cannot be empty!")
                return

            try:
                with sqlite3.connect('data.db', detect_types=sqlite3.PARSE_DECLTYPES) as db:
                    cursor = db.cursor()
                    cursor.execute("SELECT * FROM users WHERE username=?", (username,))
                    user = cursor.fetchone()

                if not user:
                    self.send(Fore.RED + f"No account found for '{username}'!")
                    return
                if user[2] != password:
                    self.send(Fore.RED + "Incorrect password!")
                    return

                try:
                    date_end = datetime.datetime.strptime(user[4], '%Y-%m-%d')
                    if date_end < datetime.datetime.now():
                        self.send(Fore.RED + "Your subscription has expired! Contact @ZzTLINHzZ.")
                        return
                except ValueError:
                    self.send(Fore.RED + f"Invalid date format for user '{username}' in database. Contact admin.")
                    return

            except sqlite3.Error as e:
                self.send(Fore.RED + f"Database error during login: {str(e)}")
                logging.error(f"Database error during login: {str(e)}")
                return

            self.send(UI.CLEAR_SCREEN, False)
            self.send(UI.main_banner(), escape=False)
            handler = CommandHandler(username, self.wfile)
            handler._draw_prompt()

            while True:
                raw_data = self.rfile.readline()
                if not raw_data:
                    self.send(Fore.YELLOW + "Connection lost. Please reconnect.")
                    break
                command = self._filter_telnet_negotiation(raw_data)
                if command:
                    handler.execute(command)
        except SystemExit:
            pass
        except Exception as e:
            self.send(Fore.RED + f"Session error: {str(e)}")
            logging.error(f"Handler error: {str(e)}")

    def _get_login_input(self, prompt):
        try:
            self.send(f"{Fore.CYAN}{prompt}{Fore.RESET}", False)
            raw_data = self.rfile.readline()
            if not raw_data:
                self.send(Fore.YELLOW + "No input received. Please try again.")
                return ""
            return self._filter_telnet_negotiation(raw_data, remove_special=True)
        except (BrokenPipeError, ConnectionError, OSError):
            self.send(Fore.RED + "Connection lost during input.")
            logging.error("Connection lost during input")
            return ""
        except Exception as e:
            self.send(Fore.RED + f"Error during input: {str(e)}")
            logging.error(f"Error during input: {str(e)}")
            return ""

    def _filter_telnet_negotiation(self, raw_data, remove_special=False):
        try:
            data = raw_data
            while b'\xff' in data:
                idx = data.index(b'\xff')
                if idx + 2 <= len(data):
                    data = data[:idx] + data[idx + 2:]
                elif idx + 1 <= len(data):
                    data = data[:idx] + data[idx + 1:]
                else:
                    data = data[:idx]
            try:
                cleaned = data.decode('utf-8').strip()
            except UnicodeDecodeError:
                cleaned = data.decode('windows-1252', errors='replace').strip()
            if remove_special:
                cleaned = ''.join(c for c in cleaned if c.isalnum() or c in '@._-')
            return cleaned
        except Exception as e:
            logging.error(f"Error in telnet negotiation: {str(e)}")
            return ""

    def send(self, data, escape=True, reset=True):
        try:
            if reset:
                data += Fore.RESET + "\033[49m"
            if escape:
                data += '\r\n'
            if not self.wfile.closed:
                self.wfile.write(data.encode('utf-8'))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionError, OSError):
            logging.error("Connection lost during send")
            raise SystemExit

# --- Telnet Handler cho chế độ bảo trì ---
class MaintenanceTelnetHandler(socketserver.StreamRequestHandler):
    def handle(self):
        try:
            logging.debug("Sending maintenance banner")
            self.wfile.write(MaintenanceUI.maintenance_banner().encode('utf-8'))
            self.wfile.flush()

            logging.debug("Starting countdown")
            for remaining in range(10, -1, -1):
                countdown_msg = f"\r{Fore.YELLOW}        Kết nối sẽ đóng trong {remaining} giây...{Fore.RESET}"
                try:
                    self.wfile.write(countdown_msg.encode('utf-8'))
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionError, OSError) as e:
                    logging.info(f"Client disconnected during countdown: {str(e)}")
                    return
                if remaining > 0:
                    time.sleep(1)

            logging.debug("Sending connection closed message")
            try:
                self.wfile.write(f"\r\n{Fore.RED}Kết nối đã đóng.{Fore.RESET}\r\n".encode('utf-8'))
                self.wfile.flush()
            except (BrokenPipeError, ConnectionError, OSError) as e:
                logging.info(f"Client disconnected at end of countdown: {str(e)}")
        except Exception as e:
            logging.error(f"Unexpected error in maintenance mode: {str(e)}")
        finally:
            logging.debug("Closing connection")
            self.finish()

# --- Telnet Server Setup ---
class TelnetServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

def main():
    try:
        with sqlite3.connect('data.db') as db:
            cursor = db.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT,
                    lever TEXT,
                    date_end TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS spam_states (
                    phone TEXT PRIMARY KEY,
                    method TEXT,
                    start_time TEXT,
                    end_time TEXT
                )
            """)
            db.commit()

        server = TelnetServer((host, port), MaintenanceTelnetHandler if MAINTENANCE_MODE else TelnetHandler)
        print(Fore.GREEN + f"MOON SPAM Telnet Server running on port {port} {'(Maintenance Mode)' if MAINTENANCE_MODE else ''}")
        server.serve_forever()
    except Exception as e:
        print(Fore.RED + f"Server error: {e}")
        logging.error(f"Main error: {str(e)}")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(Fore.YELLOW + "Server stopped by user.")