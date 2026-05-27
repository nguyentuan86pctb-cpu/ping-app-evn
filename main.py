# -*- coding: utf-8 -*-
"""
APP DI ĐỘNG GIÁM SÁT ĐO XA (EVN FIELD PING TOOL)
Tác giả: Chuyên gia Lập trình Cao cấp (Senior Full-Stack Engineer)
Vai trò: Quét ping thiết bị trong mạng WAN EVN và đồng bộ kết quả lên máy chủ Web trung tâm.
Tính năng đặc biệt: Hỗ trợ cấu trúc 4 cột (Tên thiết bị, Router, IP Thiết bị, IP SIM),
                    quét ping thực tế bằng IP SIM và hộp thoại Giám sát sâu.
"""

import os
import json
import re
import platform
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
import requests

# Cấu hình Kivy để thiết kế giao diện mượt mà và không bị ép tỷ lệ xấu
from kivy.config import Config
Config.set('graphics', 'width', '400')
Config.set('graphics', 'height', '700')

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.properties import StringProperty, NumericProperty, ListProperty
from kivy.clock import Clock

# ==========================================
# 1. KHAI BÁO GIAO DIỆN BẰNG NGÔN NGỮ KV
# ==========================================
KV_DESIGN = """
BoxLayout:
    orientation: 'vertical'
    canvas.before:
        Color:
            rgba: (0.06, 0.09, 0.16, 1) # Nền tối Slate Navy cực sang trọng
        Rectangle:
            pos: self.pos
            size: self.size

    # --- TIÊU ĐỀ ỨNG DỤNG ---
    BoxLayout:
        size_hint_y: None
        height: dp(65)
        padding: dp(15)
        canvas.before:
            Color:
                rgba: (0.09, 0.13, 0.24, 1) # Viền tiêu đề hơi sáng hơn
            Rectangle:
                pos: self.pos
                size: self.size
            Color:
                rgba: (0.22, 0.74, 0.97, 0.3) # Sọc neon xanh lam ở dưới cùng tiêu đề
            Line:
                points: [self.x, self.y, self.x + self.width, self.y]
                width: dp(1.5)

        Label:
            text: "EVN FIELD PING TOOL"
            font_size: '20sp'
            bold: True
            halign: 'left'
            valign: 'middle'
            color: (0.22, 0.74, 0.97, 1) # Chữ neon màu xanh lam nhạt

    # --- KHU VỰC CẤU HÌNH SERVER ---
    BoxLayout:
        orientation: 'vertical'
        size_hint_y: None
        height: dp(120)
        padding: dp(15)
        spacing: dp(10)
        canvas.before:
            Color:
                rgba: (0.1, 0.14, 0.26, 0.5)
            Rectangle:
                pos: self.pos
                size: self.size

        Label:
            text: "Địa chỉ Web Server trung tâm:"
            font_size: '14sp'
            size_hint_y: None
            height: dp(20)
            color: (0.58, 0.64, 0.72, 1)
            halign: 'left'
            text_size: self.size

        BoxLayout:
            orientation: 'horizontal'
            spacing: dp(10)
            size_hint_y: None
            height: dp(45)

            TextInput:
                id: server_input
                text: app.server_url
                multiline: False
                hint_text: "http://192.168.1.100:5000"
                font_size: '15sp'
                padding_y: [dp(12), dp(12)]
                background_normal: ''
                background_color: (0.06, 0.08, 0.15, 1)
                foreground_color: (1, 1, 1, 1)
                cursor_color: (0.22, 0.74, 0.97, 1)
                border: [1, 1, 1, 1]
                on_text_validate: app.save_config(server_input.text)

            Button:
                text: "LƯU URL"
                bold: True
                size_hint_x: None
                width: dp(90)
                background_normal: ''
                background_color: (0.1, 0.35, 0.6, 1)
                color: (1, 1, 1, 1)
                on_release: app.save_config(server_input.text)

    # --- THANH TIẾN TRÌNH & THÔNG BÁO ---
    BoxLayout:
        orientation: 'vertical'
        size_hint_y: None
        height: dp(80)
        padding: [dp(15), dp(10)]
        spacing: dp(5)

        Label:
            id: status_label
            text: app.status_text
            font_size: '13sp'
            bold: True
            color: (0.98, 0.57, 0.24, 1)
            halign: 'left'
            text_size: self.size

        # Thanh tiến trình quét thủ công đẹp mắt
        BoxLayout:
            size_hint_y: None
            height: dp(8)
            canvas.before:
                Color:
                    rgba: (0.1, 0.13, 0.22, 1)
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [dp(4)]
                Color:
                    rgba: (0.29, 0.87, 0.5, 1) if app.progress_percent > 0 else (0,0,0,0)
                RoundedRectangle:
                    pos: self.pos
                    size: (self.width * (app.progress_percent / 100.0), self.height)
                    radius: [dp(4)]

        BoxLayout:
            orientation: 'horizontal'
            size_hint_y: None
            height: dp(15)
            
            Label:
                text: "Chạm thiết bị để Ping sâu bằng IP SIM"
                font_size: '11sp'
                color: (0.22, 0.74, 0.97, 0.8)
                halign: 'left'
                text_size: self.size

            Label:
                text: "Tiến độ: " + str(app.progress_percent) + "% (" + str(app.scanned_count) + "/" + str(app.total_count) + ")"
                font_size: '11sp'
                color: (0.58, 0.64, 0.72, 1)
                halign: 'right'
                text_size: self.size

    # --- DANH SÁCH THIẾT BỊ ĐO XA ---
    BoxLayout:
        orientation: 'vertical'
        padding: [dp(15), 0, dp(15), dp(10)]

        Label:
            text: "DANH SÁCH THIẾT BỊ ĐÃ TẢI:"
            font_size: '12sp'
            bold: True
            size_hint_y: None
            height: dp(20)
            color: (0.22, 0.74, 0.97, 1)
            halign: 'left'
            text_size: self.size
            margin_bottom: dp(5)

        ScrollView:
            id: scroll_view
            canvas.before:
                Color:
                    rgba: (0.09, 0.12, 0.22, 0.6)
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [dp(12)]
            
            BoxLayout:
                id: device_list_container
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                padding: dp(10)
                spacing: dp(8)

    # --- BỘ 3 NÚT CHỨC NĂNG CHÍNH ---
    BoxLayout:
        orientation: 'horizontal'
        size_hint_y: None
        height: dp(80)
        padding: dp(12)
        spacing: dp(10)
        canvas.before:
            Color:
                rgba: (0.09, 0.12, 0.22, 1)
            Rectangle:
                pos: self.pos
                size: self.size

        # Nút 1: TẢI DANH SÁCH
        Button:
            text: "1. TẢI\\nDANH SÁCH"
            halign: 'center'
            valign: 'middle'
            bold: True
            font_size: '13sp'
            background_normal: ''
            background_color: (0.15, 0.55, 0.85, 1)
            color: (1, 1, 1, 1)
            on_release: app.download_devices()

        # Nút 2: BẮT ĐẦU PING
        Button:
            text: "2. QUÉT\\nPING"
            halign: 'center'
            valign: 'middle'
            bold: True
            font_size: '14sp'
            background_normal: ''
            background_color: (0.18, 0.73, 0.4, 1)
            color: (1, 1, 1, 1)
            on_release: app.start_ping_scan()

        # Nút 3: ĐỒNG BỘ LÊN WEB
        Button:
            text: "3. ĐỒNG BỘ\\nLÊN WEB"
            halign: 'center'
            valign: 'middle'
            bold: True
            font_size: '13sp'
            background_normal: ''
            background_color: (0.88, 0.45, 0.18, 1)
            color: (1, 1, 1, 1)
            on_release: app.upload_results()
"""

# ==========================================
# 2. KHAI BÁO HỘP THOẠI GIÁM SÁT SÂU (DEEP PING POPUP)
# ==========================================
class DeepPingPopup(Popup):
    """Cửa sổ nổi hiển thị màn hình console giám sát sâu ping liên tục từng thiết bị (Ping bằng IP SIM)"""
    
    def __init__(self, device_name, ip_sim, **kwargs):
        super(DeepPingPopup, self).__init__(**kwargs)
        self.device_name = device_name
        self.ip = ip_sim # Địa chỉ ping thực tế là IP SIM!
        self.ping_process = None
        self.is_pinging = False
        self.title = f"GIÁM SÁT SÂU: {device_name} - IP SIM: {ip_sim}"
        self.title_align = 'center'
        self.title_color = [0.22, 0.74, 0.97, 1]
        self.size_hint = (0.95, 0.85)
        self.auto_dismiss = False
        
        main_layout = BoxLayout(orientation='vertical', padding=15, spacing=12)
        
        with main_layout.canvas.before:
            from kivy.graphics import Color, Rectangle
            Color(0.06, 0.09, 0.16, 1)
            self.rect = Rectangle(pos=main_layout.pos, size=main_layout.size)
        main_layout.bind(pos=self._update_rect, size=self._update_rect)
        
        guide_label = Label(
            text="Đang gửi gói tin ICMP tới IP SIM. Nhấn [BẮT ĐẦU PING] để xem.",
            font_size='12sp',
            size_hint_y=None,
            height=20,
            color=[0.58, 0.64, 0.72, 1],
            halign='left'
        )
        guide_label.bind(size=guide_label.setter('text_size'))
        main_layout.add_widget(guide_label)

        self.scroll_view = ScrollView()
        with self.scroll_view.canvas.before:
            Color(0, 0, 0, 1) # Nền đen sâu
            from kivy.graphics import RoundedRectangle
            self.terminal_bg = RoundedRectangle(pos=self.scroll_view.pos, size=self.scroll_view.size, radius=[6])
        self.scroll_view.bind(pos=self._update_terminal_bg, size=self._update_terminal_bg)
        
        self.console_output = TextInput(
            text="--- HỆ THỐNG GIÁM SÁT SÂU SẴN SÀNG ---\nNhấn nút phía dưới để bắt đầu gửi lệnh Ping...\n",
            readonly=True,
            background_normal='',
            background_color=[0, 0, 0, 0],
            foreground_color=[0, 1, 0, 1], # Màu xanh lá neon
            font_size='12sp',
            size_hint_y=None,
            padding=[10, 10]
        )
        self.console_output.bind(minimum_height=self.console_output.setter('height'))
        self.scroll_view.add_widget(self.console_output)
        main_layout.add_widget(self.scroll_view)
        
        button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=10)
        
        self.btn_start = Button(
            text="BẮT ĐẦU PING",
            bold=True,
            background_normal='',
            background_color=[0.18, 0.73, 0.4, 1],
            color=[1, 1, 1, 1]
        )
        self.btn_start.bind(on_release=self.start_deep_ping)
        
        self.btn_stop = Button(
            text="DỪNG PING",
            bold=True,
            background_normal='',
            background_color=[0.97, 0.44, 0.44, 1],
            color=[1, 1, 1, 1],
            disabled=True
        )
        self.btn_stop.bind(on_release=self.stop_deep_ping)
        
        btn_close = Button(
            text="ĐÓNG HỘP THOẠI",
            bold=True,
            background_normal='',
            background_color=[0.4, 0.4, 0.4, 1]
        )
        btn_close.bind(on_release=self.close_popup)
        
        button_layout.add_widget(self.btn_start)
        button_layout.add_widget(self.btn_stop)
        button_layout.add_widget(btn_close)
        
        main_layout.add_widget(button_layout)
        self.content = main_layout

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def _update_terminal_bg(self, instance, value):
        self.terminal_bg.pos = instance.pos
        self.terminal_bg.size = instance.size

    def start_deep_ping(self, *args):
        if self.is_pinging:
            return
            
        self.is_pinging = True
        self.btn_start.disabled = True
        self.btn_stop.disabled = False
        self.console_output.text = f"--- Khởi động tiến trình PING liên tục tới IP SIM: {self.ip} ---\n\n"
        
        threading.Thread(target=self._ping_stream_thread, daemon=True).start()

    def _ping_stream_thread(self):
        current_os = platform.system().lower()
        if "windows" in current_os:
            cmd = ["ping", "-t", self.ip]
        else:
            cmd = ["ping", self.ip]
            
        try:
            startupinfo = None
            if "windows" in current_os:
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
            self.ping_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="ignore",
                startupinfo=startupinfo
            )
            
            while self.is_pinging and self.ping_process:
                line = self.ping_process.stdout.readline()
                if not line:
                    break
                
                Clock.schedule_once(lambda dt, l=line: self._append_log(l))
                
        except Exception as e:
            Clock.schedule_once(lambda dt: self._append_log(f"\n[LỖI HỆ THỐNG]: {str(e)}\n"))
        finally:
            self.is_pinging = False
            Clock.schedule_once(lambda dt: self._on_ping_stopped())

    def _append_log(self, text):
        self.console_output.text += text
        self.scroll_view.scroll_y = 0

    def _on_ping_stopped(self):
        self.btn_start.disabled = False
        self.btn_stop.disabled = True

    def stop_deep_ping(self, *args):
        if not self.is_pinging:
            return
            
        self.is_pinging = False
        if self.ping_process:
            try:
                self.ping_process.terminate()
                self.ping_process.kill()
            except:
                pass
            self.ping_process = None
            
        self.console_output.text += "\n--- ĐÃ DỪNG TIẾN TRÌNH PING THEO YÊU CẦU ---\n"

    def close_popup(self, *args):
        self.stop_deep_ping()
        self.dismiss()


# ==========================================
# 3. KHAI BÁO DÒNG HIỂN THỊ THIẾT BỊ (DEVICE ROW)
# ==========================================
class DeviceRowWidget(BoxLayout):
    """Widget dòng hiển thị thông tin 4 cột: Tên, Router, IP Thiết bị, IP SIM"""
    
    def __init__(self, index, name, router, ip_device, ip_sim, status="Chưa quét", latency="N/A", **kwargs):
        super(DeviceRowWidget, self).__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = 110 # Chiều cao dòng
        self.padding = [15, 12]
        self.spacing = 10
        self.index = index
        self.device_name = name
        self.router = router
        self.ip_device = ip_device
        self.ip_sim = ip_sim # Lưu lại IP SIM phục vụ chạm để Deep Ping
        
        # Vẽ nền Glassmorphism bo tròn viền
        with self.canvas.before:
            if index % 2 == 0:
                self.color_bg = (0.13, 0.17, 0.29, 0.8)
            else:
                self.color_bg = (0.1, 0.14, 0.24, 0.8)
                
            from kivy.graphics import Color, RoundedRectangle, Line
            self.draw_bg_color = Color(*self.color_bg)
            self.draw_bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[8])
            self.draw_border_color = Color(0.2, 0.25, 0.4, 0.3)
            self.draw_border_line = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, 8), width=1)
            
        self.bind(pos=self.update_canvas, size=self.update_canvas)

        # Cột trái: Tên trạm, Tên Router & Thông tin IP (Thiết bị vs SIM)
        left_layout = BoxLayout(orientation='vertical', size_hint_x=0.65, spacing=3)
        
        self.name_label = Label(
            text=name, 
            font_size='14sp', 
            bold=True, 
            color=(1, 1, 1, 1),
            halign='left',
            valign='middle'
        )
        self.name_label.bind(size=self.name_label.setter('text_size'))
        
        self.router_label = Label(
            text="Router: " + router, 
            font_size='11sp', 
            color=(0.58, 0.64, 0.72, 1),
            halign='left',
            valign='middle'
        )
        self.router_label.bind(size=self.router_label.setter('text_size'))
        
        self.ip_label = Label(
            text=f"DEV: {ip_device} | SIM: {ip_sim}", 
            font_size='11sp', 
            color=(0.22, 0.74, 0.97, 1),
            halign='left',
            valign='middle'
        )
        self.ip_label.bind(size=self.ip_label.setter('text_size'))
        
        left_layout.add_widget(self.name_label)
        left_layout.add_widget(self.router_label)
        left_layout.add_widget(self.ip_label)

        # Cột phải: Trạng thái Online/Offline & Latency ms
        right_layout = BoxLayout(orientation='vertical', size_hint_x=0.35, spacing=4)
        
        self.status_label = Label(
            text=status, 
            font_size='13sp', 
            bold=True,
            halign='right',
            valign='middle'
        )
        self.status_label.bind(size=self.status_label.setter('text_size'))
        self.set_status_color(status)
        
        self.latency_label = Label(
            text=latency, 
            font_size='12sp', 
            color=(0.58, 0.64, 0.72, 1),
            halign='right',
            valign='middle'
        )
        self.latency_label.bind(size=self.latency_label.setter('text_size'))
        
        right_layout.add_widget(self.status_label)
        right_layout.add_widget(self.latency_label)

        self.add_widget(left_layout)
        self.add_widget(right_layout)

    def update_canvas(self, *args):
        self.draw_bg_rect.pos = self.pos
        self.draw_bg_rect.size = self.size
        self.draw_border_line.rounded_rectangle = (self.x, self.y, self.width, self.height, 8)

    def set_status_color(self, status):
        if status == "Online":
            self.status_label.color = (0.29, 0.87, 0.5, 1)
        elif status == "Offline":
            self.status_label.color = (0.97, 0.44, 0.44, 1)
        else:
            self.status_label.color = (0.98, 0.57, 0.24, 1)

    def update_scan_result(self, status, latency):
        self.status_label.text = status
        self.latency_label.text = latency
        self.set_status_color(status)

    def on_touch_down(self, touch):
        """Chạm vào dòng để mở Popup giám sát sâu hướng tới IP SIM"""
        if self.collide_point(*touch.pos):
            # Mở Popup Deep Ping truyền địa chỉ ip_sim làm mục tiêu quét
            popup = DeepPingPopup(device_name=self.device_name, ip_sim=self.ip_sim)
            popup.open()
            return True
        return super(DeviceRowWidget, self).on_touch_down(touch)


# ==========================================
# 4. CLASS CHÍNH ỨNG DỤNG (TELEMETRY APP)
# ==========================================
class TelemetryApp(App):
    server_url = StringProperty("http://127.0.0.1:5000")
    status_text = StringProperty("Sẵn sàng. Hãy tải danh sách thiết bị.")
    
    total_count = NumericProperty(0)
    scanned_count = NumericProperty(0)
    progress_percent = NumericProperty(0)
    
    def __init__(self, **kwargs):
        super(TelemetryApp, self).__init__(**kwargs)
        self.devices = []       # Lưu danh sách thiết bị tải từ server
        self.scan_results = {}  # Lưu kết quả theo IP SIM: { ip_sim: {"status": status, "latency": latency} }
        self.widget_map = {}    # Ánh xạ nhanh IP SIM sang DeviceRowWidget
        self.is_scanning = False
        self.config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        self.load_config()

    def build(self):
        self.title = "EVN Telemetry Field Ping"
        return Builder.load_string(KV_DESIGN)

    # ==========================================
    # 5. QUẢN LÝ CẤU HÌNH CỤC BỘ
    # ==========================================
    def load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.server_url = data.get("server_url", "http://127.0.0.1:5000")
        except Exception as e:
            print(f"Không thể đọc file cấu hình: {e}")

    def save_config(self, url):
        self.server_url = url.strip()
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump({"server_url": self.server_url}, f, ensure_ascii=False, indent=4)
            self.show_status(f"Đã lưu địa chỉ Server: {self.server_url}", error=False)
        except Exception as e:
            self.show_status(f"Lỗi lưu cấu hình: {str(e)}", error=True)

    def show_status(self, text, error=False):
        def update_label(dt):
            self.status_label = self.root.ids.status_label
            self.status_label.text = text
            if error:
                self.status_label.color = (0.97, 0.44, 0.44, 1)
            else:
                self.status_label.color = (0.22, 0.74, 0.97, 1)
        Clock.schedule_once(update_label)

    # ==========================================
    # 6. XỬ LÝ LẤY DANH SÁCH TỪ WEB SERVER (4 CỘT)
    # ==========================================
    def download_devices(self):
        if self.is_scanning:
            self.show_status("Đang quét ping, vui lòng chờ quét xong!", error=True)
            return
            
        self.show_status("Đang kết nối tải danh sách thiết bị...")
        threading.Thread(target=self._download_devices_thread, daemon=True).start()

    def _download_devices_thread(self):
        url = f"{self.server_url.rstrip('/')}/api/get_devices"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                devices_data = response.json()
                
                # Đồng bộ lưu trữ và ánh xạ theo IP SIM làm khóa duy nhất!
                self.devices = devices_data
                self.scan_results = {d["ip_sim"]: {"status": "Chưa quét", "latency": "N/A"} for d in devices_data}
                
                Clock.schedule_once(lambda dt: self._update_device_list_ui(devices_data))
                self.show_status(f"Đã tải về thành công {len(devices_data)} thiết bị đo xa!", error=False)
            else:
                self.show_status(f"Lỗi máy chủ trả về mã: {response.status_code}", error=True)
        except requests.exceptions.RequestException as e:
            self.show_status("Không thể kết nối Server! Vui lòng kiểm tra mạng/URL.", error=True)

    def _update_device_list_ui(self, devices_data):
        container = self.root.ids.device_list_container
        container.clear_widgets()
        self.widget_map.clear()
        
        self.total_count = len(devices_data)
        self.scanned_count = 0
        self.progress_percent = 0

        if not devices_data:
            container.add_widget(Label(
                text="Máy chủ không có thiết bị nào.\\nHãy thêm thiết bị trên Web Dashboard.", 
                size_hint_y=None, 
                height=100,
                color=(0.58, 0.64, 0.72, 1)
            ))
            return

        for idx, item in enumerate(devices_data):
            # Khởi tạo widget hiển thị đầy đủ 4 cột thông tin
            row_widget = DeviceRowWidget(
                index=idx, 
                name=item["name"], 
                router=item["router"],
                ip_device=item["ip_device"],
                ip_sim=item["ip_sim"],
                status="Chưa quét",
                latency="N/A"
            )
            container.add_widget(row_widget)
            # Ánh xạ theo IP SIM làm khóa!
            self.widget_map[item["ip_sim"]] = row_widget

    # ==========================================
    # 7. ENGINE PING ĐỒNG LOẠT THEO IP SIM (CONCURRENT)
    # ==========================================
    def start_ping_scan(self):
        if self.is_scanning:
            self.show_status("Đang trong quá trình quét, không thể quét lại!", error=True)
            return
            
        if not self.devices:
            self.show_status("Vui lòng click [TẢI DANH SÁCH] trước khi quét!", error=True)
            return
            
        self.is_scanning = True
        self.scanned_count = 0
        self.progress_percent = 0
        self.show_status("Bắt đầu quét đồng loạt địa chỉ IP SIM...")
        
        for ip_sim, widget in self.widget_map.items():
            widget.update_scan_result("Đang quét...", "Chờ...")

        threading.Thread(target=self._run_parallel_ping, daemon=True).start()

    def _run_parallel_ping(self):
        max_workers = min(15, len(self.devices)) 
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Quét ping hướng tới địa chỉ IP SIM!
            futures = [executor.submit(self._ping_single_ip, item["ip_sim"]) for item in self.devices]
            
            for future in futures:
                future.result()
                
        self.is_scanning = False
        self.show_status("Hoàn tất quét IP SIM! Hãy nhấn [ĐỒNG BỘ LÊN WEB] để tải lên.", error=False)

    def _ping_single_ip(self, ip_sim):
        """Thực hiện ping một địa chỉ IP SIM tĩnh của trạm"""
        current_os = platform.system().lower()
        
        if "windows" in current_os:
            cmd = ["ping", "-n", "1", "-w", "2000", ip_sim]
        else:
            cmd = ["ping", "-c", "1", "-w", "2", ip_sim]
            
        status = "Offline"
        latency = "Không phản hồi"
        
        try:
            startupinfo = None
            if "windows" in current_os:
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="ignore",
                startupinfo=startupinfo
            )
            stdout, stderr = process.communicate(timeout=3)
            
            if process.returncode == 0:
                match = re.search(r'(?:time|thời\s+gian)\s*[=<]\s*([\d\.]+)\s*(?:ms)?', stdout, re.IGNORECASE)
                if match:
                    ms_str = match.group(1)
                    try:
                        ms_val = float(ms_str)
                        if ms_val < 1:
                            latency = "<1 ms"
                        else:
                            latency = f"{int(round(ms_val))} ms"
                    except:
                        latency = f"{ms_str} ms"
                    status = "Online"
                else:
                    status = "Online"
                    latency = "<10 ms"
                    
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except:
                pass
        except Exception as e:
            print(f"Lỗi khi thực hiện ping IP SIM {ip_sim}: {e}")
            
        # Lưu kết quả theo IP SIM
        self.scan_results[ip_sim] = {"status": status, "latency": latency}
        
        Clock.schedule_once(lambda dt: self._update_single_widget_ui(ip_sim, status, latency))

    def _update_single_widget_ui(self, ip_sim, status, latency):
        if ip_sim in self.widget_map:
            self.widget_map[ip_sim].update_scan_result(status, latency)
            
        self.scanned_count += 1
        if self.total_count > 0:
            self.progress_percent = int((self.scanned_count / self.total_count) * 100)

    # ==========================================
    # 8. ĐỒNG BỘ KẾT QUẢ QUÉT LÊN WEB SERVER (DỰA TRÊN IP SIM)
    # ==========================================
    def upload_results(self):
        if self.is_scanning:
            self.show_status("Đang quét ping, vui lòng chờ hoàn thành!", error=True)
            return
            
        if not self.scan_results:
            self.show_status("Không có dữ liệu quét để đồng bộ!", error=True)
            return
            
        self.show_status("Đang đồng bộ kết quả lên máy chủ Web...")
        threading.Thread(target=self._upload_results_thread, daemon=True).start()

    def _upload_results_thread(self):
        url = f"{self.server_url.rstrip('/')}/api/update_results"
        
        # Đóng gói kết quả gửi lên khớp theo trường ip_sim
        payload = []
        for ip_sim, res in self.scan_results.items():
            if res["status"] != "Chưa quét":
                payload.append({
                    "ip_sim": ip_sim,
                    "status": res["status"],
                    "latency": res["latency"]
                })
                
        if not payload:
            self.show_status("Chưa quét thiết bị nào! Hãy chạy Quét Ping trước.", error=True)
            return
            
        try:
            headers = {'Content-Type': 'application/json'}
            response = requests.post(url, json=payload, headers=headers, timeout=8)
            
            if response.status_code == 200:
                res_data = response.json()
                self.show_status(f"Đồng bộ thành công! {res_data.get('message', '')}", error=False)
            else:
                self.show_status(f"Đồng bộ thất bại. Máy chủ báo mã lỗi: {response.status_code}", error=True)
        except requests.exceptions.RequestException as e:
            self.show_status("Không thể kết nối Server để đồng bộ! Kiểm tra mạng Wi-Fi/4G.", error=True)


if __name__ == "__main__":
    TelemetryApp().run()
