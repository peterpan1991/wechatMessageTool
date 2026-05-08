import flet as ft
import os
import sys
import re
import threading
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.wechat_search_core import WechatSearchCore
from core.wechat_parser_core import WechatParserCore


COLORS = {
    'bg_primary': '#F8FAFC',
    'bg_secondary': '#F1F5F9',
    'card': '#FFFFFF',
    'accent': '#6366F1',
    'accent_hover': '#4F46E5',
    'success': '#10B981',
    'warning': '#F59E0B',
    'error': '#EF4444',
    'text_primary': '#1E293B',
    'text_secondary': '#64748B',
    'text_light': '#94A3B8',
    'border': '#E2E8F0',
}

@ft.control
class WechatFletApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "微信工具箱"
        self.page.padding = 0
        self.page.window_width = 1000
        self.page.window_height = 750
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.theme = ft.Theme(
            color_scheme_seed="#6366F1",
            font_family="Microsoft YaHei",
        )
        
        self.folder_path = ""
        self.keyword = ""
        self.search_mode = "keyword"
        
        self.search_core = WechatSearchCore()
        self.parser_core = WechatParserCore()
        self.wechat_user = None
        
        self.search_results = []
        
        self.search_result_count = None
        self.search_progress = None
        self.search_results_view = None
        self.search_status = None
        self.export_status = None
        self.export_progress = None
        self.folder_field = None
        self.search_folder_field = None
        self.keyword_field = None
        self.search_mode_dropdown = None

        self.create_ui()
    
    def create_ui(self):
        self.page.clean()
        
        main_container = ft.SafeArea(
            expand=True,
            content=ft.Container(
                content=ft.Column([
                self.create_header(),
                self.create_tabs(),
            ], spacing=0, expand=True),
            expand=True,
            bgcolor=COLORS['bg_primary'],
        ))
        
        self.page.add(main_container)
    
    def create_header(self):
        return ft.Container(
            content=ft.Row([
                ft.Column([
                    ft.Text("微信工具箱", size=28, weight=ft.FontWeight.BOLD, 
                           color=COLORS['text_primary']),
                    ft.Text("消息搜索 · 流水导出", size=12, color=COLORS['text_secondary']),
                ], spacing=2, expand=True),
            ], alignment=ft.MainAxisAlignment.START),
            padding=ft.Padding.only(left=30, right=30, top=0, bottom=20),
            bgcolor=COLORS['card'],
            border=ft.Border.only(bottom=ft.border.BorderSide(1, COLORS['border'])),
        )
    
    def create_tabs(self):
        self.search_tab = self.create_search_tab()
        self.export_tab = self.create_export_tab()
        
        tabBar = ft.TabBar(
            scrollable=False,
            tabs=[
                ft.Tab(
                    label="消息搜索"
                ),
                ft.Tab(
                    label="流水导出",
                ),
            ],
        )

        tabs = ft.Tabs(
            selected_index=0,
            length=2,
            expand=True,
            content= ft.Column(
                expand=True,
                spacing=20,
                controls=[
                    tabBar,
                    ft.TabBarView(
                        expand=True,
                        controls=[
                            ft.Container(
                                alignment=ft.Alignment.CENTER,
                                content=self.search_tab,
                                expand=True,
                                padding=20,
                            ),
                            ft.Container(
                                alignment=ft.Alignment.CENTER,
                                content=self.export_tab,
                                expand=True,
                                padding=20,
                            )                            
                        ],
                    ),
                ]
            ),
        )
        
        return ft.Container(content=tabs, expand=True)
    
    def create_search_tab(self):
        self.search_status = ft.Text("请选择文件夹并输入关键字", size=12, color=COLORS['text_secondary'])
        
        input_card = self.create_card([
            self.create_folder_input(),
            self.create_search_field(),
            self.create_status_bar(),
        ])
        
        self.search_result_count = ft.Text("", size=13, color=COLORS['success'])
        self.search_progress = ft.ProgressBar(width=float('inf'), visible=False, color=COLORS['accent'])

        self.search_results_view = ft.ListView(
            spacing=10,
            padding=20,
            expand=True,
            auto_scroll=True,
            controls=[
                ft.Container(
                    content=ft.Text("请选择文件夹并输入关键字开始搜索", 
                                  color=COLORS['text_secondary'], size=13),
                    padding=20,
                )
            ],
        )
        
        result_card = ft.Container(
            expand=True,
            content=self.create_card([
                ft.Container(
                    content=ft.Row([
                        ft.Text("搜索结果", size=16, weight=ft.FontWeight.W_600, 
                               color=COLORS['text_primary']),
                        self.search_result_count,
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    margin=ft.Margin.only(bottom=15),
                ),
                self.search_progress,
                self.search_results_view,
            ]),
        )
        
        return ft.Column([
            input_card,
            result_card,
        ], spacing=20, expand=True)
    
    def create_export_tab(self):
        self.export_status = ft.Text("请选择文件夹", size=12, color=COLORS['text_secondary'])
        self.export_progress = ft.ProgressBar(width=float('inf'), visible=False, color=COLORS['success'])
        
        card = self.create_card([
            ft.Container(
                content=ft.Column([                    
                    ft.Text("流水导出", size=18, weight=ft.FontWeight.W_600, 
                           color=COLORS['text_primary']),
                    ft.Text("将微信聊天记录中的流水交易记录导出为Excel文件", 
                           size=12, color=COLORS['text_secondary']),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=ft.Padding.only(top=20, bottom=10),
            ),
            self.create_folder_field("HTML文件夹"),
            self.export_status,
            self.export_progress,
            ft.Container(
                content=ft.Button(
                    icon=ft.Icons.DOWNLOAD,
                    content="导出流水记录",
                    style=ft.ButtonStyle(
                        bgcolor=COLORS['success'],
                        color="#FFFFFF",
                        padding=15,
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                    on_click=self.handle_export_records,
                ),
                alignment=ft.Alignment(0, 0),
                padding=ft.Padding.only(top=10, bottom=20),
            ),
        ])
        
        return ft.Column([
            card
        ], spacing=20, expand=True)
    
    def create_card(self, contents):
        return ft.Container(
            content=ft.Column(contents, spacing=15, tight=True, expand=True),
            bgcolor=COLORS['card'],
            border_radius=12,
            padding=25,
            border=ft.Border.all(1, COLORS['border']),
        )
    
    def create_folder_input(self):
        self.search_folder_field = ft.TextField(
            label="消息文件夹",
            hint_text="点击右侧按钮选择文件夹",
            border_color=COLORS['border'],
            focused_border_color=COLORS['accent'],
            text_size=13,
            expand=True,
            read_only=True,
            prefix_icon="folder",
        )

        return  ft.SafeArea(
            expand=True,
            content=ft.Container(
                content=ft.Row([
                    self.search_folder_field,
                    ft.IconButton(
                        icon=ft.Icons.DRIVE_FOLDER_UPLOAD,
                        selected_icon=ft.Icons.DRIVE_FOLDER_UPLOAD_ROUNDED,
                        tooltip="浏览文件夹",
                        on_click=self.handle_pick_directory,
                        style=ft.ButtonStyle(
                            bgcolor=COLORS['bg_secondary'],
                            shape=ft.RoundedRectangleBorder(radius=8),
                        ),
                    ),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                margin=ft.Margin.only(bottom=15),
            )
        )
    
    def create_folder_field(self, label):
        self.folder_field = ft.TextField(
            label=label,
            hint_text="点击右侧按钮选择文件夹",
            border_color=COLORS['border'],
            focused_border_color=COLORS['accent'],
            text_size=13,
            expand=True,
            read_only=True,
            prefix_icon="folder",
        )

        return ft.Container(
            content=ft.Row([
                self.folder_field,
                ft.IconButton(
                    icon=ft.Icons.DRIVE_FOLDER_UPLOAD,
                    selected_icon=ft.Icons.DRIVE_FOLDER_UPLOAD_ROUNDED,
                    tooltip="浏览文件夹",
                    on_click=self.handle_pick_directory,
                    style=ft.ButtonStyle(
                        bgcolor=COLORS['bg_secondary'],
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                ),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        )
    
    def create_search_field(self):
        self.keyword_field = ft.TextField(
            label="关键字",
            hint_text="输入搜索关键字",
            border_color=COLORS['border'],
            focused_border_color=COLORS['accent'],
            text_size=13,
            on_submit=lambda _: self.start_search(),
            expand=True,
        )
        
        self.search_mode_dropdown = ft.SegmentedButton(
            on_change=self.on_search_mode_change,
            selected_icon=ft.Icon(ft.Icons.CHECK_SHARP),
            selected=["keyword"],
            allow_multiple_selection=False,
            segments=[
                ft.Segment(
                    value="keyword",
                    label=ft.Text("关键词匹配"),
                ),
                ft.Segment(
                    value="semantic",
                    label=ft.Text("AI语义搜索"),
                ),
            ],
        )

        search_button = ft.Button(
            icon=ft.Icons.SEARCH,
            content="开始搜索", 
            style=ft.ButtonStyle(
                bgcolor=COLORS['accent'],
                color="#FFFFFF",
                padding=15,
            ),
            on_click=lambda _: self.start_search(),
        )
        
        return ft.Container(
            content=ft.Row([
                self.keyword_field,
                self.search_mode_dropdown,
                search_button,
            ], spacing=15, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            margin=ft.Margin.only(bottom=15),
        )
    
    def create_status_bar(self):
        return ft.Container(
            content=self.search_status,
            padding=ft.Padding.only(top=10),
        )
    
    def on_search_mode_change(self, e):
        selected = e.control.selected
        if selected:
            self.search_mode = list(selected)[0]
    
    async def handle_pick_directory(self):
        self.search_core.clear_page_cache()
        
        path = await ft.FilePicker().get_directory_path()
        
        if path:
            self.folder_path = path
            
            if self.search_folder_field:
                self.search_folder_field.value = self.folder_path
                self.search_folder_field.update()
            
            if self.folder_field:
                self.folder_field.value = self.folder_path
                self.folder_field.update()
            
            navbar_path = os.path.join(path, 'navbar.html')
            if os.path.exists(navbar_path):
                self.wechat_user = self.parser_core.get_wechat_user(navbar_path)
                self.export_status.value = f"已加载: {self.wechat_user or '未知用户'}"
                self.export_status.update()

    def start_search(self, e=None):
        folder = self.folder_path
        keyword = self.keyword_field.value.strip() if self.keyword_field.value else ""
        
        if not folder:
            self.show_dialog("提示", "请先选择文件夹！")
            return
        
        if not keyword:
            self.show_dialog("提示", "请输入搜索关键字！")
            return
        
        self.search_results_view.controls = [
            ft.Container(
                content=ft.Text("正在搜索...", color=COLORS['text_secondary'], size=13),
                padding=20,
            )
        ]
        self.search_results_view.update()
        self.search_progress.visible = True
        self.search_progress.update()
        self.search_status.value = "正在搜索..."
        self.search_status.update()
        self.search_result_count.value = ""
        self.search_result_count.update()
        
        search_start_time = time.time()
        
        thread = threading.Thread(target=self.run_search, args=(folder, keyword, self.search_mode, search_start_time))
        thread.daemon = True
        thread.start()
    
    def run_search(self, folder, keyword, search_mode, search_start_time):
        try:
            success, result = self.search_core.search_folder(
                folder, keyword, search_mode, self.update_search_progress
            )
            
            if not success:
                self.page.run_thread(self.on_search_error, result)
                return
            
            self.search_results = result
            self.page.run_thread(self.display_results, keyword, search_mode, folder, search_start_time)
            
        except Exception as e:
            self.page.run_thread(self.on_search_error, str(e))
    
    def display_results(self, keyword, search_mode, folder, search_start_time):
        self.search_progress.visible = False
        self.search_progress.update()
        
        elapsed_time = time.time() - search_start_time
        if elapsed_time < 60:
            time_text = f"{elapsed_time:.1f} 秒"
        else:
            minutes = int(elapsed_time // 60)
            seconds = elapsed_time % 60
            time_text = f"{minutes} 分 {seconds:.1f} 秒"
        
        if not self.search_results:
            self.search_results_view.controls = [
                ft.Container(
                    content=ft.Text(
                        f"未找到与 '{keyword}' 相关内容", 
                        color=COLORS['text_secondary'], size=13
                    ),
                    padding=20,
                )
            ]
            self.search_results_view.update()
            self.search_status.value = "搜索完成"
            self.search_result_count.value = f"0 条结果 · {time_text}"
            self.search_status.update()
            self.search_result_count.update()
            return
        
        result_items = []
        
        for result in self.search_results:
            chat_name = result['chat_name']
            sender = result.get('sender', '')
            send_time = result.get('send_time', '')
            message = result.get('message', '')
            path = result.get('path', result.get('page', ''))

            full_path = os.path.join(folder, path).replace('\\', '/')
            full_path = 'file:///' + full_path
            
            score_text = ""
            if search_mode == 'semantic':
                score = result.get('score', 0)
                score_text = f"相似度: {score:.2f}"
            else:
                score_text = "相似度: 1.00"
            
            result_items.append(
                ft.Container(
                    content=ft.Column([
                        ft.Row([                            
                            ft.Text(score_text, size=12, color=COLORS['success'], weight=ft.FontWeight.W_600),
                            ft.Container(expand=True),
                            ft.Text(chat_name, size=13, color=COLORS['accent'], weight=ft.FontWeight.W_600),
                        ]),
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.ACCOUNT_CIRCLE),
                                ft.Text(f"{sender}  {send_time}", size=11, color=COLORS['text_light']),
                            ]
                        ),
                        ft.Container(
                            content=ft.Text(message, size=12, color=COLORS['text_primary'], selectable=True),
                            padding=ft.Padding.only(top=8, bottom=8),
                        ),
                        ft.TextButton(
                            content=ft.Row(
                                [
                                    ft.Icon(ft.Icons.INSERT_DRIVE_FILE_OUTLINED, size=12),
                                    ft.Text(f"{full_path}", size=10, color=COLORS['text_light']),
                                ]
                            ),
                            on_click=lambda e, p=full_path: self.open_in_browser(p),
                        )                        
                    ], spacing=4),
                    padding=15,
                    bgcolor=COLORS['bg_secondary'],
                    border_radius=8,
                    margin=ft.Margin.only(bottom=10),
                )
            )
        
        self.search_results_view.controls = result_items
        self.search_results_view.update()
        
        self.search_status.value = "搜索完成"
        self.search_result_count.value = f"{len(self.search_results)} 条结果 · {time_text}"
        self.search_status.update()
        self.search_result_count.update()
    
    def update_search_progress(self, message, progress=0):
        def update_ui_status():
            self.search_status.value = message
            self.search_status.update()
        self.page.run_thread(update_ui_status)
    
    def on_search_error(self, message):
        self.search_progress.visible = False
        self.search_progress.update()
        self.search_status.value = "搜索出错"
        self.search_status.update()
        self.show_dialog("错误", message)
    
    async def handle_export_records(self, folder):
        folder = self.folder_path
        if not folder:
            self.show_dialog("提示", "请先选择HTML文件夹！")
            return
        
        safe_name = re.sub(r'[\\/:*?"<>|]', '_', self.wechat_user or 'wechat_transactions')

        path = await ft.FilePicker().save_file(
            dialog_title="保存Excel文件",
            file_name=f"{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            allowed_extensions=["xlsx"],
        )
        
        if path:
            save_path = path
            self.export_progress.visible = True
            self.export_progress.update()
            self.export_status.value = "正在处理，请稍候..."
            self.export_status.update()
            
            thread = threading.Thread(target=self.run_export, args=(folder, save_path))
            thread.daemon = True
            thread.start()
    
    def run_export(self, folder, save_path):
        try:
            success, result = self.parser_core.process_folder(folder, self.update_export_progress)
            
            if not success:
                self.page.run_thread(self.on_export_error, result)
                return
            
            records, wechat_user = result
            
            if not records:
                self.page.run_thread(self.on_export_error, "未找到任何流水记录")
                return
            
            self.export_status.value = "正在生成Excel..."
            self.export_status.update()
            self.parser_core.create_excel(records, save_path)
            
            self.page.run_thread(self.on_export_success, len(records), save_path)
            
        except Exception as e:
            self.page.run_thread(self.on_export_error, str(e))
    
    def update_export_progress(self, message, progress=0):
        def update_ui():
            self.export_status.value = message
            self.export_status.update()
        self.page.run_thread(update_ui)
    
    def on_export_success(self, count, path):
        self.export_progress.visible = False
        self.export_progress.update()
        self.export_status.value = "导出完成"
        self.export_status.update()
        
        self.show_dialog("成功", f"导出完成！\n\n共导出 {count} 条记录\n保存位置: {path}")
        
        folder = os.path.dirname(path)
        os.startfile(folder)
    
    def on_export_error(self, message):
        self.export_progress.visible = False
        self.export_progress.update()
        self.export_status.value = "导出出错"
        self.export_status.update()
        self.show_dialog("错误", message)
    
    def open_in_browser(self, url):
        import webbrowser
        webbrowser.open(url)
    
    def show_dialog(self, title, message):
        dialog = ft.AlertDialog(
            title=ft.Text(title),
            content=ft.Text(message),
            actions=[ft.TextButton("确定", on_click=lambda e: self.page.pop_dialog())],
            open=True,
        )

        self.page.show_dialog(dialog)


def main(page: ft.Page):
    WechatFletApp(page)


if __name__ == '__main__':
    ft.run(main)
