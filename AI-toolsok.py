import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import requests
import json
import threading
from datetime import datetime
import webbrowser
import os
import re
import sys
import tempfile

def get_program_dir():
    """获取程序所在目录（兼容 PyInstaller/Nuitka 打包）"""
    if getattr(sys, 'frozen', False):
        # 打包成 exe 时，__file__ 不可靠，用 sys.executable
        return os.path.dirname(os.path.abspath(sys.executable))
    else:
        return os.path.dirname(os.path.abspath(__file__))

def get_work_dir():
    """获取用户工作目录（非临时目录）"""
    cwd = os.getcwd()
    # 如果当前工作目录不是临时目录，优先使用
    if not is_temp_directory(cwd):
        return cwd
    # 其次使用用户文档目录
    docs = os.path.expanduser("~/Documents")
    if os.path.isdir(docs):
        return docs
    # 然后使用桌面
    desktop = os.path.expanduser("~/Desktop")
    if os.path.isdir(desktop):
        return desktop
    # 最后使用用户主目录
    return os.path.expanduser("~")

def is_temp_directory(path):
    """检测路径是否是临时目录（如 _MEI* 等打包运行时目录）"""
    abs_path = os.path.abspath(path)
    temp_dirs = [
        tempfile.gettempdir(),
        os.path.expanduser("~\\AppData\\Local\\Temp"),
        "C:\\Windows\\Temp",
        "/tmp",
        "/var/tmp",
    ]
    # 检查是否在临时目录下
    for td in temp_dirs:
        try:
            if abs_path.startswith(os.path.abspath(td)):
                return True
        except:
            pass
    # 检查 _MEI 标志（PyInstaller 运行时）
    if "_MEI" in abs_path:
        return True
    return False

class DeepSeekClient:
    VERSION = 1.001  # 程序版本号
    
    def __init__(self, root):
        self.root = root
        self.root.title("DeepSeek AI 助手 · 专业版   v1.001  作者:靳好宝 邮箱:uulov@qq.com")
        self.root.geometry("1000x750")
        
        # 配置默认值
        self.config = {
            "api_key": "",  # 留空，首次使用时提示
            "api_url": "https://api.deepseek.com/v1/chat/completions",
            "temperature": 0.7,
            "max_tokens": 2000,
            "model": "deepseek-v4-flash",
            "provider": "deepseek",  # deepseek / nvidia / openai / custom
            "nvidia_api_key": "",  # 英伟达API密钥
            "nvidia_api_url": "https://integrate.api.nvidia.com/v1/chat/completions",
            "nvidia_model": "deepseek-ai/deepseek-v4-flash",
            # OpenAI 兼容模型设置
            "openai_api_key": "",
            "openai_api_url": "https://api.openai.com/v1/chat/completions",
            "openai_model": "gpt-4o-mini",
            # 自定义模型设置（任意 OpenAI 兼容 API）
            "custom_api_key": "",
            "custom_api_url": "",
            "custom_model": "",
            "custom_name": "",  # 自定义服务商名称
            "version": 1.000  # 保存版本号
        }
        
        # 状态变量
        self.messages = []
        self.current_response = ""
        self.streaming = False
        self.is_dark_mode = False
        
        # Token统计
        self.total_tokens = 0  # 累计token使用量
        self.today_tokens = 0  # 当日token使用量
        self.today_date = datetime.now().strftime("%Y-%m-%d")  # 当前日期
        
        # 设置保存目录
        self.setup_save_directory()
        
        self.load_config()
        self.load_token_usage()  # 加载token使用记录
        self.load_chat_history()  # 加载历史对话列表
        self.setup_ui()
        self.apply_theme()
        
        if not self.config["api_key"] and self.config["provider"] == "deepseek":
            self.show_settings()
        
        # 程序退出时自动保存对话
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # 设置程序图标
        try:
            icon_path = "C:\\Users\\Administrator\\workspace\\icon.ico"
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except:
            pass
    
    def setup_save_directory(self):
        """创建保存文件的目录（始终在程序目录下）"""
        # 程序目录（配置和数据的固定位置）
        self.app_dir = get_program_dir()
        # 工作目录（文件对话框用）
        self.work_dir = get_work_dir()
        # 保存目录固定在程序目录下
        self.save_dir = os.path.join(self.app_dir, "chat_history")
        
        if not os.path.exists(self.save_dir):
            try:
                os.makedirs(self.save_dir)
                print(f"创建保存目录: {self.save_dir}")
            except Exception as e:
                print(f"创建目录失败: {e}")
                self.save_dir = self.app_dir
        
        self.token_file = os.path.join(self.save_dir, "token.ini")
        self.today_token_file = os.path.join(self.save_dir, "today_token.ini")
    
    def estimate_tokens(self, text):
        """估算token数量"""
        if not text:
            return 0
        
        chinese_pattern = re.compile(r'[\u4e00-\u9fff]')
        chinese_chars = len(chinese_pattern.findall(text))
        english_chars = len(re.sub(r'[\u4e00-\u9fff]', '', text))
        estimated = chinese_chars + (english_chars / 3.5)
        return int(estimated)
    
    def update_token_display(self):
        """更新token显示"""
        today_info = f"今日: {self.today_tokens} | 总计: {self.total_tokens}"
        self.token_var.set(f"📊 {today_info}")
        self.save_token_usage()
    
    def check_and_reset_daily_tokens(self):
        """检查并重置当日token计数"""
        current_date = datetime.now().strftime("%Y-%m-%d")
        if current_date != self.today_date:
            self.today_tokens = 0
            self.today_date = current_date
            self.save_token_usage()
    
    def add_tokens(self, text):
        """添加token使用量"""
        tokens = self.estimate_tokens(text)
        self.total_tokens += tokens
        self.today_tokens += tokens
        self.update_token_display()
        return tokens
    
    def load_token_usage(self):
        """加载token使用记录"""
        try:
            # 加载总token
            if os.path.exists(self.token_file):
                with open(self.token_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        self.total_tokens = int(content)
                    else:
                        self.total_tokens = 0
            else:
                self.total_tokens = 0
            
            # 加载今日token
            if os.path.exists(self.today_token_file):
                with open(self.today_token_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.today_date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
                    self.today_tokens = data.get("tokens", 0)
                    
                    # 如果日期不是今天，重置
                    current_date = datetime.now().strftime("%Y-%m-%d")
                    if self.today_date != current_date:
                        self.today_tokens = 0
                        self.today_date = current_date
            else:
                self.today_tokens = 0
                self.today_date = datetime.now().strftime("%Y-%m-%d")
                
        except Exception as e:
            print(f"加载token记录失败: {e}")
            self.total_tokens = 0
            self.today_tokens = 0
            self.today_date = datetime.now().strftime("%Y-%m-%d")
    
    def save_token_usage(self):
        """保存token使用记录"""
        try:
            # 保存总token
            with open(self.token_file, "w", encoding="utf-8") as f:
                f.write(str(self.total_tokens))
            
            # 保存今日token
            with open(self.today_token_file, "w", encoding="utf-8") as f:
                json.dump({
                    "date": self.today_date,
                    "tokens": self.today_tokens
                }, f)
        except Exception as e:
            print(f"保存token记录失败: {e}")
    
    def save_chat_history_to_file(self):
        """保存对话历史到文件"""
        if not self.messages:
            return None
        
        first_message = ""
        for msg in self.messages:
            if msg["role"] == "user":
                first_message = msg["content"][:20] + "..." if len(msg["content"]) > 20 else msg["content"]
                break
        
        # 清理文件名中的非法字符
        safe_name = re.sub(r'[\\/:*?"<>|]', '', first_message) if first_message else "新对话"
        filename = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_name}.json"
        filepath = os.path.join(self.save_dir, filename)
        
        try:
            chat_data = {
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "messages": self.messages,
                "preview": first_message,
                "provider": self.config["provider"],
                "model": self.get_current_model()
            }
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(chat_data, f, ensure_ascii=False, indent=2)
            
            return filepath
        except Exception as e:
            print(f"保存对话历史失败: {e}")
            return None
    
    def load_chat_history(self):
        """加载历史对话列表"""
        self.sessions = []
        self.session_count = 0
        
        try:
            if os.path.exists(self.save_dir):
                for filename in os.listdir(self.save_dir):
                    if filename.startswith("chat_") and filename.endswith(".json"):
                        filepath = os.path.join(self.save_dir, filename)
                        try:
                            with open(filepath, "r", encoding="utf-8") as f:
                                chat_data = json.load(f)
                            
                            time_str = filename[5:20]
                            try:
                                dt = datetime.strptime(time_str, '%Y%m%d_%H%M%S')
                                display_time = dt.strftime('%m-%d %H:%M')
                            except:
                                display_time = "未知时间"
                            
                            preview = chat_data.get("preview", "新对话")
                            if not preview:
                                preview = "新对话"
                            
                            session_name = f"{display_time} - {preview}"
                            
                            self.sessions.append({
                                "name": session_name,
                                "filepath": filepath,
                                "messages": chat_data.get("messages", []),
                                "timestamp": chat_data.get("timestamp", "")
                            })
                        except Exception as e:
                            print(f"加载历史文件失败 {filename}: {e}")
                
                self.sessions.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
                self.session_count = len(self.sessions)
        except Exception as e:
            print(f"加载历史对话列表失败: {e}")
    
    def refresh_session_list(self):
        """刷新会话列表显示"""
        self.session_listbox.delete(0, tk.END)
        for session in self.sessions:
            self.session_listbox.insert(tk.END, session["name"])
    
    def get_provider_display_name(self):
        """获取当前服务商显示名称"""
        name_map = {
            "deepseek": "DeepSeek",
            "nvidia": "英伟达免费模型",
            "openai": "OpenAI",
            "custom": self.config.get("custom_name") or "自定义模型"
        }
        return name_map.get(self.config["provider"], self.config["provider"])
    
    def get_current_model(self):
        """获取当前使用的模型"""
        if self.config["provider"] == "deepseek":
            return self.config["model"]
        elif self.config["provider"] == "nvidia":
            return self.config["nvidia_model"]
        elif self.config["provider"] == "openai":
            return self.config.get("openai_model", "gpt-4o-mini")
        elif self.config["provider"] == "custom":
            return self.config.get("custom_model", "")
        return self.config["model"]
    
    def get_save_path(self, filename):
        return os.path.join(self.save_dir, filename)
    
    def setup_ui(self):
        self.root.configure(bg="#f0f0f0")  # 程序背景浅灰色
        self.create_menu()
        
        self.main_container = tk.Frame(self.root, bg="#f0f0f0")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.create_sidebar()
        self.create_chat_area()
        self.create_statusbar()

    def create_rounded_button(self, parent, text, command, color, emoji="", width=None):
        """创建圆角风格按钮（使用白色文字、指定颜色）"""
        btn_text = f" {emoji} {text}" if emoji else f" {text}"
        btn = tk.Button(parent, text=btn_text, command=command,
                       bg=color, fg="white", 
                       font=("微软雅黑", 9, "bold"),
                       bd=0, padx=10, pady=4,
                       activebackground=color, activeforeground="white",
                       cursor="hand2", relief=tk.FLAT,
                       highlightthickness=0)
        if width:
            btn.config(width=width)
        return btn

    def create_menu(self):
        menubar = tk.Menu(self.root, bg="#ffffff", fg="#333333",
                         activebackground="#4B9956", activeforeground="white",
                         font=("微软雅黑", 9))
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0, font=("微软雅黑", 9))
        menubar.add_cascade(label="📁 文件", menu=file_menu)
        file_menu.add_command(label="📄 新建对话", accelerator="Ctrl+N", command=self.new_chat)
        file_menu.add_command(label="💾 保存对话(TXT)", command=self.save_chat_txt)
        file_menu.add_command(label="🌐 导出HTML", command=self.export_html)
        file_menu.add_command(label="📂 打开保存文件夹", command=self.open_save_folder)
        file_menu.add_separator()
        file_menu.add_command(label="❌ 退出", command=self.root.quit)
        
        edit_menu = tk.Menu(menubar, tearoff=0, font=("微软雅黑", 9))
        menubar.add_cascade(label="✏️ 编辑", menu=edit_menu)
        edit_menu.add_command(label="📋 复制最后回复", accelerator="Ctrl+C", command=self.copy_last_response)
        edit_menu.add_command(label="🗑️ 清空对话", command=self.clear_chat)
        edit_menu.add_command(label="🔄 重置Token计数", command=self.reset_token_count)
        
        settings_menu = tk.Menu(menubar, tearoff=0, font=("微软雅黑", 9))
        menubar.add_cascade(label="⚙️ 设置", menu=settings_menu)
        settings_menu.add_command(label="🔑 API设置", command=self.show_settings)
        settings_menu.add_command(label="🎨 切换主题", command=self.toggle_theme)
        
        help_menu = tk.Menu(menubar, tearoff=0, font=("微软雅黑", 9))
        menubar.add_cascade(label="❓ 帮助", menu=help_menu)
        help_menu.add_command(label="📖 使用说明", command=self.show_help)
        help_menu.add_command(label="🔗 获取DeepSeek API密钥", command=lambda: webbrowser.open("https://platform.deepseek.com"))
        help_menu.add_command(label="🔗 获取英伟达API密钥", command=lambda: webbrowser.open("https://build.nvidia.com/"))
        help_menu.add_separator()
        help_menu.add_command(label="ℹ️ 关于", command=self.show_about)
        
        # 厂商切换菜单
        provider_menu = tk.Menu(menubar, tearoff=0, font=("微软雅黑", 9))
        menubar.add_cascade(label="🏢 厂商", menu=provider_menu)
        self.provider_var_menu = tk.StringVar(value=self.config["provider"])
        provider_menu.add_radiobutton(label="🤖 DeepSeek", variable=self.provider_var_menu,
                                      value="deepseek", command=lambda: self.switch_provider("deepseek"))
        provider_menu.add_radiobutton(label="🆓 英伟达免费模型", variable=self.provider_var_menu,
                                      value="nvidia", command=lambda: self.switch_provider("nvidia"))
        provider_menu.add_radiobutton(label="🔵 OpenAI", variable=self.provider_var_menu,
                                      value="openai", command=lambda: self.switch_provider("openai"))
        provider_menu.add_radiobutton(label="⚙️ 自定义模型", variable=self.provider_var_menu,
                                      value="custom", command=lambda: self.switch_provider("custom"))
        
        self.root.bind("<Control-n>", lambda e: self.new_chat())
        self.root.bind("<Control-s>", lambda e: self.save_chat_txt())
        self.root.bind("<Control-c>", lambda e: self.copy_last_response())
    
    def switch_provider(self, provider):
        """一键切换服务商"""
        if provider == self.config["provider"]:
            return
        # 检查密钥
        if provider == "nvidia" and not self.config["nvidia_api_key"]:
            messagebox.showwarning("提示", "请先在设置中配置英伟达API密钥")
            self.show_settings()
            return
        if provider == "openai" and not self.config["openai_api_key"]:
            messagebox.showwarning("提示", "请先在设置中配置OpenAI API密钥")
            self.show_settings()
            return
        if provider == "custom" and not (self.config.get("custom_api_key") and self.config.get("custom_api_url")):
            messagebox.showwarning("提示", "请先在设置中配置自定义模型的API密钥和地址")
            self.show_settings()
            return
        if provider == "deepseek" and not self.config["api_key"]:
            messagebox.showwarning("提示", "请先在设置中配置DeepSeek API密钥")
            self.show_settings()
            return
        self.config["provider"] = provider
        self.provider_var_menu.set(provider)  # 同步菜单选中状态
        self.save_config()
        self.update_model_list()
        self.model_combo.set(self.get_current_model())
        provider_name = self.get_provider_display_name()
        model_name = self.get_current_model()
        self.update_status(f"已切换到: {provider_name} · {model_name}")
        # 更新厂商标签
        if hasattr(self, 'provider_label'):
            self.provider_label.config(text=f"🏢 {provider_name}")
        # 添加系统提示
        self.add_message("系统", f"已切换到 {provider_name}\n   模型: {model_name}", "system")
    
    def create_sidebar(self):
        self.sidebar = tk.Frame(self.main_container, width=220, bg="#f0f0f0")
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        self.sidebar.pack_propagate(False)
        
        title_frame = tk.Frame(self.sidebar, bg="#f0f0f0")
        title_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(title_frame, text="📜 对话历史", font=("微软雅黑", 11, "bold"),
                bg="#f0f0f0", fg="black").pack(side=tk.LEFT)
        # 刷新按钮（圆角风格，第二行颜色 #2E7D32）
        refresh_btn = self.create_rounded_button(title_frame, "↻", self.refresh_history, "#2E7D32", "🔄")
        refresh_btn.pack(side=tk.RIGHT)
        
        self.session_listbox = tk.Listbox(self.sidebar, height=20, font=("微软雅黑", 9),
                                          bg="white", fg="#333333",
                                          relief=tk.FLAT, highlightthickness=1,
                                          highlightcolor="#add8e6", highlightbackground="#add8e6",
                                          selectbackground="#4B9956", selectforeground="white")
        self.session_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        self.session_listbox.bind('<<ListboxSelect>>', self.on_session_select)
        
        self.refresh_session_list()
    
    def refresh_history(self):
        self.load_chat_history()
        self.refresh_session_list()
        self.update_status("已刷新历史列表")
    
    def create_chat_area(self):
        self.chat_frame = tk.Frame(self.main_container, bg="#f0f0f0")
        self.chat_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.chat_display = scrolledtext.ScrolledText(
            self.chat_frame, wrap=tk.WORD, font=("微软雅黑", 11),
            bg="white", fg="#212529",
            relief=tk.FLAT, borderwidth=2,
            highlightthickness=1, highlightcolor="#add8e6",
            highlightbackground="#add8e6", padx=10, pady=10
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        
        self.setup_text_tags()
        self.chat_display.config(state=tk.DISABLED)
        
        self.create_toolbar()
        self.create_input_area()
    
    def setup_text_tags(self):
        self.chat_display.tag_config("user", foreground="#0d6efd", font=("微软雅黑", 11, "bold"))
        self.chat_display.tag_config("assistant", foreground="#198754", font=("微软雅黑", 11, "bold"))
        self.chat_display.tag_config("system", foreground="#6c757d", font=("微软雅黑", 10, "italic"))
        self.chat_display.tag_config("time", foreground="#adb5bd", font=("微软雅黑", 9))
        
        self.chat_display.tag_config("code", background="#f1f3f5", font=("Consolas", 10))
        
        self.create_context_menu()
    
    def create_context_menu(self):
        self.context_menu = tk.Menu(self.chat_display, tearoff=0, font=("微软雅黑", 9))
        self.context_menu.add_command(label="📋 复制", command=self.copy_selected)
        self.context_menu.add_command(label="📄 复制全部", command=self.copy_all)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🗑️ 清空对话", command=self.clear_chat)
        
        self.chat_display.bind("<Button-3>", self.show_context_menu)
    
    def create_toolbar(self):
        self.toolbar = tk.Frame(self.chat_frame, bg="#f0f0f0")
        self.toolbar.pack(fill=tk.X, pady=(5, 0))
        
        left_tools = tk.Frame(self.toolbar, bg="#f0f0f0")
        left_tools.pack(side=tk.LEFT)
        
        # 第一行按钮颜色 #4B9956
        self.create_rounded_button(left_tools, "新建", self.new_chat, "#4B9956", "🆕").pack(side=tk.LEFT, padx=2)
        self.create_rounded_button(left_tools, "复制回复", self.copy_last_response, "#2E7D32", "📋").pack(side=tk.LEFT, padx=2)
        self.create_rounded_button(left_tools, "保存TXT", self.save_chat_txt, "#4B9956", "💾").pack(side=tk.LEFT, padx=2)
        
        right_tools = tk.Frame(self.toolbar, bg="#f0f0f0")
        right_tools.pack(side=tk.RIGHT)
        
        # 模型选择下拉框
        tk.Label(right_tools, text="🤖 模型:", font=("微软雅黑", 9), bg="#f0f0f0", fg="black").pack(side=tk.RIGHT, padx=(5, 2))
        self.model_combo = ttk.Combobox(right_tools, width=30, state="readonly", font=("微软雅黑", 9))
        self.model_combo.pack(side=tk.RIGHT, padx=5)
        self.model_combo.bind("<<ComboboxSelected>>", self.on_model_change)
        
        # 第二行按钮颜色 #2E7D32
        self.stop_btn = self.create_rounded_button(right_tools, "停止", self.stop_generating, "#2E7D32", "⏹️")
        self.stop_btn.config(state=tk.DISABLED)
        self.stop_btn.pack(side=tk.RIGHT, padx=2)
        
        self.create_rounded_button(right_tools, "清空", self.clear_chat, "#4B9956", "🗑️").pack(side=tk.RIGHT, padx=2)
        
        self.update_model_list()
    
    def update_model_list(self):
        """更新模型下拉列表"""
        if self.config["provider"] == "deepseek":
            self.model_combo.config(state="readonly")
            models = ["deepseek-v4-flash", "deepseek-v4-pro"]
        elif self.config["provider"] == "nvidia":
            # 英伟达模式 - 支持手动输入
            self.model_combo.config(state="normal")
            models = ["手动输入...", "deepseek-ai/deepseek-v4-flash", "deepseek-ai/deepseek-v4-pro",
                     "meta/llama-3.2-3b-instruct", "meta/llama-3.2-1b-instruct", 
                     "meta/llama-3.1-8b-instruct", "meta/llama-3.1-70b-instruct",
                     "mistralai/mistral-7b-instruct-v0.3", "google/gemma-2-2b-it",
                     "google/gemma-2-9b-it", "microsoft/phi-3-mini-128k-instruct",
                     "qwen/qwen2-7b-instruct"]
        elif self.config["provider"] == "openai":
            # OpenAI 模式 - 支持手动输入
            self.model_combo.config(state="normal")
            models = ["手动输入...", "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o1",
                     "gpt-3.5-turbo", "claude-sonnet-4-20250514", "claude-haiku-3-5-20241022"]
        else:
            # 自定义模型模式 - 完全手动输入
            self.model_combo.config(state="normal")
            models = ["手动输入..."]
        
        self.model_combo['values'] = models
        self.model_combo.set(self.get_current_model())
        
        if self.config["provider"] in ("nvidia", "openai", "custom"):
            self.model_combo.bind("<FocusIn>", self.on_model_focus)
            self.model_combo.bind("<KeyRelease>", self.on_model_manual_input)
    
    def on_model_focus(self, event):
        """模型输入框获得焦点时的处理"""
        current = self.model_combo.get()
        if current == "手动输入...":
            self.model_combo.set("")
    
    def on_model_manual_input(self, event):
        """手动输入模型名称"""
        # 允许用户手动输入任意模型名称
        pass
    
    def on_model_change(self, event):
        """模型选择改变时的处理"""
        selected = self.model_combo.get()
        if selected and selected != "手动输入...":
            if self.config["provider"] == "deepseek":
                self.config["model"] = selected
            elif self.config["provider"] == "nvidia":
                self.config["nvidia_model"] = selected
            elif self.config["provider"] == "openai":
                self.config["openai_model"] = selected
            else:
                self.config["custom_model"] = selected
            self.save_config()
            self.update_status(f"已切换到模型: {selected}")
    
    def create_input_area(self):
        self.input_frame = tk.Frame(self.chat_frame, bg="#f0f0f0")
        self.input_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.input_text = tk.Text(self.input_frame, height=4, font=("微软雅黑", 10),
                                  wrap=tk.WORD, relief=tk.FLAT, borderwidth=2,
                                  padx=10, pady=10, bg="white", fg="#333333",
                                  highlightthickness=1, highlightcolor="#add8e6",
                                  highlightbackground="#add8e6")
        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        scrollbar = ttk.Scrollbar(self.input_frame, orient=tk.VERTICAL, command=self.input_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.input_text.config(yscrollcommand=scrollbar.set)
        
        button_frame = tk.Frame(self.chat_frame, bg="#f0f0f0")
        button_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.input_text.bind("<Return>", lambda e: self.send_message())
        
        # 左侧：当前厂商（标签加 emoji，黑色文字）
        provider_name = self.get_provider_display_name()
        self.provider_label = tk.Label(button_frame, text=f"🏢 {provider_name}", font=("微软雅黑", 9, "bold"),
                                      bg="#f0f0f0", fg="black")
        self.provider_label.pack(side=tk.LEFT, padx=5)
        
        # 右侧：发送按钮（颜色 #4B9956，第一行颜色）→ 粘贴按钮（颜色 #2E7D32，第二行颜色）
        self.send_btn = self.create_rounded_button(button_frame, "发送 (Enter)", self.send_message, "#4B9956", "📤")
        self.send_btn.pack(side=tk.RIGHT)
        
        paste_btn = self.create_rounded_button(button_frame, "粘贴", self.paste_to_input, "#2E7D32", "📋")
        paste_btn.pack(side=tk.RIGHT, padx=5)
    
    def create_statusbar(self):
        self.statusbar = tk.Frame(self.root, bg="#f0f0f0")
        self.statusbar.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=5)
        
        self.status_label = tk.Label(self.statusbar, text="DeepSeek API 已连接",
                                    font=("微软雅黑", 9), bg="#f0f0f0", fg="black")
        self.status_label.pack(side=tk.LEFT)
        
        self.token_var = tk.StringVar(value="📊 加载中...")
        self.token_label = tk.Label(self.statusbar, textvariable=self.token_var,
                                   font=("微软雅黑", 9, "bold"), bg="#f0f0f0", fg="black")
        self.token_label.pack(side=tk.RIGHT, padx=10)
        
        save_dir_text = f"📁 {os.path.basename(self.save_dir)}"
        self.save_dir_label = tk.Label(self.statusbar, text=save_dir_text,
                                      font=("微软雅黑", 9), bg="#f0f0f0", fg="black")
        self.save_dir_label.pack(side=tk.RIGHT, padx=10)
        
        # 初始化token显示
        self.update_token_display()
    
    def reset_token_count(self):
        if messagebox.askyesno("确认", "确定要重置Token计数吗？\n\n这将同时重置总使用量和今日使用量。"):
            self.total_tokens = 0
            self.today_tokens = 0
            self.update_token_display()
            self.update_status("Token计数已重置")
    
    def show_context_menu(self, event):
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()
    
    def copy_selected(self):
        try:
            selected_text = self.chat_display.selection_get()
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
            self.update_status("已复制")
        except:
            pass
    
    def copy_all(self):
        text = self.chat_display.get("1.0", tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.update_status("已复制全部对话")
    
    def copy_last_response(self):
        if self.current_response:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.current_response)
            self.update_status("已复制最后回复")
        else:
            messagebox.showwarning("提示", "没有可复制的回复")
    
    def stop_generating(self):
        self.streaming = False
        self.stop_btn.config(state=tk.DISABLED)
        self.update_status("已停止生成")
    
    def on_close(self):
        """程序关闭时自动保存当前对话"""
        if self.messages:
            self.save_chat_history_to_file()
        self.root.destroy()
    
    def new_chat(self):
        if self.messages:
            saved_file = self.save_chat_history_to_file()
            if saved_file:
                self.load_chat_history()
                self.refresh_session_list()
        
        self.messages = []
        self.current_response = ""
        self.clear_chat()
        provider_name = self.get_provider_display_name()
        current_model = self.get_current_model()
        self.add_message("系统", f"✨ 已开启新对话\n   服务商: {provider_name}\n   模型: {current_model}", "system")
        self.update_status("新对话已创建")
    
    def on_session_select(self, event):
        if not self.session_listbox.curselection():
            return
        
        index = self.session_listbox.curselection()[0]
        if index < len(self.sessions):
            session = self.sessions[index]
            
            if self.messages:
                if not messagebox.askyesno("加载会话", "当前对话未保存，确定加载历史会话吗？"):
                    return
                self.save_chat_history_to_file()
            
            try:
                with open(session["filepath"], "r", encoding="utf-8") as f:
                    chat_data = json.load(f)
                
                self.messages = chat_data.get("messages", [])
                
                self.chat_display.config(state=tk.NORMAL)
                self.chat_display.delete("1.0", tk.END)
                
                for msg in self.messages:
                    if msg["role"] == "user":
                        self.add_message("你", msg["content"], "user", update_history=False)
                    elif msg["role"] == "assistant":
                        self.add_message("DeepSeek", msg["content"], "assistant", update_history=False)
                
                self.chat_display.config(state=tk.DISABLED)
                self.update_status(f"已加载: {session['name']}")
                
            except Exception as e:
                messagebox.showerror("加载失败", f"无法加载会话: {e}")
    
    def clear_chat(self):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete("1.0", tk.END)
        self.chat_display.config(state=tk.DISABLED)
    
    def get_timestamp(self):
        return datetime.now().strftime("%H:%M:%S")
    
    def add_message(self, sender, message, tag=None, update_history=True):
        self.chat_display.config(state=tk.NORMAL)
        
        self.chat_display.insert(tk.END, f"[{self.get_timestamp()}] ", "time")
        
        if sender == "你":
            self.chat_display.insert(tk.END, f"{sender}: ", "user")
            if update_history:
                self.add_tokens(message)
        elif sender == "DeepSeek":
            self.chat_display.insert(tk.END, f"{sender}: ", "assistant")
            if update_history:
                self.add_tokens(message)
        else:
            self.chat_display.insert(tk.END, f"{sender}: ", "system")
        
        self.chat_display.insert(tk.END, f"{message}\n\n", tag)
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
    
    def stream_insert(self, content):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, content)
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
    
    def start_stream_response(self):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"[{self.get_timestamp()}] ", "time")
        self.chat_display.insert(tk.END, "DeepSeek: ", "assistant")
        self.stream_pos = self.chat_display.index(tk.END)
        self.chat_display.config(state=tk.DISABLED)
        self.current_response = ""
        self.stop_btn.config(state=tk.NORMAL)
    
    def end_stream_response(self):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, "\n\n")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
        
        if self.current_response:
            self.messages.append({"role": "assistant", "content": self.current_response})
            self.add_tokens(self.current_response)
        
        self.stop_btn.config(state=tk.DISABLED)
        self.update_status("响应完成")
        # 自动保存到历史（后台执行，不阻塞UI）
        self.root.after(100, self.save_chat_history_to_file)
    
    def get_api_config(self):
        """获取当前 provider 的 API 配置（api_key, api_url, model）"""
        provider = self.config["provider"]
        if provider == "deepseek":
            return self.config["api_key"], self.config["api_url"], self.config["model"]
        elif provider == "nvidia":
            model = self.model_combo.get()
            if model == "手动输入...":
                model = self.config["nvidia_model"]
            return self.config["nvidia_api_key"], self.config["nvidia_api_url"], model
        elif provider == "openai":
            model = self.model_combo.get()
            if model == "手动输入...":
                model = self.config.get("openai_model", "gpt-4o-mini")
            return self.config["openai_api_key"], self.config["openai_api_url"], model
        else:
            model = self.model_combo.get()
            if model == "手动输入...":
                model = self.config.get("custom_model", "")
            return self.config.get("custom_api_key", ""), self.config.get("custom_api_url", ""), model
    
    def send_message(self):
        # 检查API配置
        api_key, api_url, model = self.get_api_config()
        if not api_key:
            provider_display = self.get_provider_display_name()
            messagebox.showerror("错误", f"请先在设置中配置{provider_display}的API密钥")
            self.show_settings()
            return
        if not model:
            messagebox.showerror("错误", "请先选择一个模型")
            return
        
        user_input = self.input_text.get("1.0", tk.END).strip()
        if not user_input:
            return
        
        # 检查并重置当日计数
        self.check_and_reset_daily_tokens()
        
        self.add_message("你", user_input, "user")
        self.input_text.delete("1.0", tk.END)
        
        self.send_btn.config(state=tk.DISABLED)
        self.input_text.config(state=tk.DISABLED)
        
        self.messages.append({"role": "user", "content": user_input})
        self.add_tokens(user_input)
        
        thread = threading.Thread(target=self.stream_chat)
        thread.daemon = True
        thread.start()
    
    def stream_chat(self):
        self.streaming = True
        self.root.after(0, self.start_stream_response)
        self.root.after(0, lambda: self.update_status("正在生成回复..."))
        
        try:
            api_key, api_url, model = self.get_api_config()
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            max_tokens = min(self.config.get("max_tokens", 2000), 65536)
            
            payload = {
                "model": model,
                "messages": self.messages,
                "stream": True,
                "temperature": self.config["temperature"],
                "max_tokens": max_tokens
            }
            
            max_retries = 3
            retry_delay = 2
            last_error = None
            
            for attempt in range(max_retries):
                if attempt > 0:
                    self.root.after(0, lambda: self.update_status(f"429 限流，{retry_delay}秒后重试 ({attempt}/{max_retries})..."))
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2
                
                response = requests.post(
                    api_url,
                    headers=headers,
                    json=payload,
                    stream=True,
                    timeout=60
                )
                
                if response.status_code == 429:
                    last_error = f"API错误: {response.status_code}\n{response.text[:200]}"
                    continue
                
                if response.status_code == 200:
                    for line in response.iter_lines():
                        if not self.streaming:
                            break
                        if line:
                            line = line.decode('utf-8')
                            if line.startswith("data: "):
                                data = line[6:]
                                if data == "[DONE]":
                                    break
                                try:
                                    chunk = json.loads(data)
                                    if chunk["choices"][0]["delta"].get("content"):
                                        content = chunk["choices"][0]["delta"]["content"]
                                        self.current_response += content
                                        self.root.after(0, self.stream_insert, content)
                                except:
                                    continue
                    self.root.after(0, self.end_stream_response)
                    return
                else:
                    error_msg = f"API错误: {response.status_code}\n{response.text[:200]}"
                    self.root.after(0, self.add_message, "系统", error_msg, "system")
                    return
            
            if last_error:
                self.root.after(0, self.add_message, "系统", f"{last_error}\n已重试 {max_retries} 次仍失败，请稍后再试", "system")
                
        except Exception as e:
            self.root.after(0, self.add_message, "系统", f"请求失败: {str(e)}", "system")
        finally:
            self.streaming = False
            self.root.after(0, lambda: self.send_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.input_text.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.input_text.focus())
    
    def save_chat_txt(self):
        if not self.messages:
            messagebox.showwarning("提示", "没有可保存的对话记录")
            return
        
        filename = f"deepseek_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = self.get_save_path(filename)
        
        try:
            content = self.chat_display.get("1.0", tk.END)
            
            provider_name = self.get_provider_display_name()
            header = f"DeepSeek 对话记录 (使用: {provider_name})\n"
            header += f"模型: {self.get_current_model()}\n"
            header += f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            header += f"今日Token: {self.today_tokens} | 总计Token: {self.total_tokens}\n"
            header += "=" * 50 + "\n\n"
            content = header + content
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            
            result = messagebox.askyesno("保存成功", 
                                       f"对话已保存到:\n{filepath}\n\n是否打开文件所在文件夹？")
            if result:
                self.open_file_location(filepath)
            
            self.update_status(f"已保存: {filename}")
            
        except Exception as e:
            messagebox.showerror("保存失败", str(e))
    
    def export_html(self):
        if not self.messages:
            messagebox.showwarning("提示", "没有可导出的对话")
            return
        
        filename = f"deepseek_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        filepath = self.get_save_path(filename)
        
        try:
            content = self.chat_display.get("1.0", tk.END)
            content = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            content = content.replace("\n", "<br>")
            
            provider_name = self.get_provider_display_name()
            
            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>DeepSeek 对话记录</title>
    <style>
        body {{ 
            font-family: '宋体', sans-serif; 
            max-width: 800px; 
            margin: 20px auto; 
            padding: 20px;
            background-color: #f8f9fa;
            line-height: 1.6;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background-color: #e9ecef;
            border-radius: 8px;
        }}
        .message {{ 
            margin-bottom: 20px; 
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .user-message {{
            background-color: #e3f2fd;
            border-left: 4px solid #0d6efd;
        }}
        .assistant-message {{
            background-color: #e8f5e9;
            border-left: 4px solid #198754;
        }}
        .system-message {{
            background-color: #f8f9fa;
            border-left: 4px solid #6c757d;
            font-style: italic;
        }}
        .timestamp {{ 
            color: #6c757d; 
            font-size: 12px;
            margin-bottom: 8px;
        }}
        .content {{ 
            white-space: pre-wrap;
            word-wrap: break-word;
            font-size: 14px;
            line-height: 1.6;
        }}
        .footer {{
            text-align: center;
            color: #6c757d;
            font-size: 12px;
            margin-top: 30px;
            padding: 20px;
            border-top: 1px solid #dee2e6;
        }}
        .token-info {{
            background-color: #e7f3ff;
            border: 1px solid #b8daff;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h2>DeepSeek 对话记录</h2>
        <p>使用服务: {provider_name}</p>
        <p>模型: {self.get_current_model()}</p>
        <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    <div class="token-info">
        <strong>Token使用统计:</strong> 今日: {self.today_tokens} | 总计: {self.total_tokens}
    </div>
    <div class="messages">
"""
            lines = content.split("<br>")
            for line in lines:
                if "你: " in line:
                    html_content += f'        <div class="message user-message"><div class="timestamp">用户</div><div class="content">{line}</div></div>\n'
                elif "DeepSeek: " in line:
                    html_content += f'        <div class="message assistant-message"><div class="timestamp">DeepSeek</div><div class="content">{line}</div></div>\n'
                elif "系统: " in line:
                    html_content += f'        <div class="message system-message"><div class="timestamp">系统</div><div class="content">{line}</div></div>\n'
            
            html_content += """
    </div>
    <div class="footer">
        <p>Powered by DeepSeek AI</p>
    </div>
</body>
</html>"""
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            result = messagebox.askyesno("导出成功", 
                                       f"对话已导出到:\n{filepath}\n\n是否打开文件所在文件夹？")
            if result:
                self.open_file_location(filepath)
            
            self.update_status(f"已导出: {filename}")
            
        except Exception as e:
            messagebox.showerror("导出失败", str(e))
    
    def open_file_location(self, filepath):
        try:
            if os.name == 'nt':
                os.startfile(os.path.dirname(filepath))
            elif os.name == 'posix':
                os.system(f'open "{os.path.dirname(filepath)}"')
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件夹: {e}")
    
    def open_save_folder(self):
        try:
            if os.name == 'nt':
                os.startfile(self.save_dir)
            elif os.name == 'posix':
                os.system(f'open "{self.save_dir}"')
            self.update_status(f"已打开保存文件夹: {self.save_dir}")
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件夹: {e}")
    
    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.apply_theme()
    
    def apply_theme(self):
        if self.is_dark_mode:
            bg_color = "#1e1e1e"
            fg_color = "#ffffff"
            self.root.configure(bg=bg_color)
            self.chat_display.config(bg=bg_color, fg=fg_color, insertbackground="white")
            self.chat_display.tag_config("time", foreground="#6c757d")
            self.chat_display.tag_config("code", background="#2d2d2d")
            self.token_label.config(foreground="#6ea8fe")
        else:
            bg_color = "#f0f0f0"
            fg_color = "#212529"
            self.root.configure(bg=bg_color)
            self.chat_display.config(bg="white", fg=fg_color, insertbackground="black")
            self.chat_display.tag_config("time", foreground="#adb5bd")
            self.chat_display.tag_config("code", background="#f1f3f5")
            self.token_label.config(foreground="black")
    
    def update_status(self, message):
        self.status_label.config(text=message)
    
    def paste_to_input(self):
        """粘贴剪贴板内容到输入框"""
        try:
            clipboard_content = self.root.clipboard_get()
            self.input_text.insert(tk.END, clipboard_content)
            self.input_text.focus()
            self.update_status("已粘贴到输入框")
        except:
            messagebox.showwarning("提示", "剪贴板中没有可粘贴的内容")
    
    def paste_from_clipboard(self, entry_widget):
        try:
            clipboard_content = self.root.clipboard_get()
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, clipboard_content)
            self.update_status("已粘贴API密钥")
        except:
            messagebox.showwarning("警告", "剪贴板中没有可粘贴的内容")
    
    def show_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("API设置 - 支持 DeepSeek / 英伟达 / OpenAI / 自定义")
        settings_window.geometry("780x700")
        settings_window.resizable(False, False)
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        notebook = ttk.Notebook(settings_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # DeepSeek 选项卡
        deepseek_frame = ttk.Frame(notebook, padding=20)
        notebook.add(deepseek_frame, text="DeepSeek")
        
        ttk.Label(deepseek_frame, text="API 密钥:", font=("宋体", 10)).grid(row=0, column=0, sticky=tk.W, pady=5)
        ds_key_frame = ttk.Frame(deepseek_frame)
        ds_key_frame.grid(row=0, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        ds_api_key_entry = ttk.Entry(ds_key_frame, width=45, show="*")
        ds_api_key_entry.pack(side=tk.LEFT)
        ds_api_key_entry.insert(0, self.config["api_key"])
        ds_paste_btn = ttk.Button(ds_key_frame, text="粘贴", 
                                  command=lambda: self.paste_from_clipboard(ds_api_key_entry), width=6)
        ds_paste_btn.pack(side=tk.LEFT, padx=5)
        
        ds_show_key_var = tk.BooleanVar()
        def ds_toggle_show():
            ds_api_key_entry.config(show="" if ds_show_key_var.get() else "*")
        ttk.Checkbutton(deepseek_frame, text="显示密钥", variable=ds_show_key_var, 
                       command=ds_toggle_show).grid(row=0, column=2, padx=5)
        
        ttk.Label(deepseek_frame, text="API地址:", font=("宋体", 10)).grid(row=1, column=0, sticky=tk.W, pady=5)
        ds_api_url_entry = ttk.Entry(deepseek_frame, width=50)
        ds_api_url_entry.grid(row=1, column=1, columnspan=2, sticky=tk.W, pady=5, padx=(10, 0))
        ds_api_url_entry.insert(0, self.config["api_url"])
        
        ttk.Label(deepseek_frame, text="模 型:", font=("宋体", 10)).grid(row=2, column=0, sticky=tk.W, pady=5)
        ds_model_combo = ttk.Combobox(deepseek_frame, values=["deepseek-chat", "deepseek-coder"], width=30)
        ds_model_combo.grid(row=2, column=1, columnspan=2, sticky=tk.W, pady=5, padx=(10, 0))
        ds_model_combo.set(self.config["model"])
        
        ttk.Label(deepseek_frame, text="获取密钥: platform.deepseek.com", 
                 font=("宋体", 9), foreground="#6c757d").grid(row=3, column=0, columnspan=3, pady=10, sticky=tk.W)
        
        # 英伟达选项卡 - 手动输入模式
        nvidia_frame = ttk.Frame(notebook, padding=20)
        notebook.add(nvidia_frame, text="英伟达免费模型")
        
        ttk.Label(nvidia_frame, text="API 密钥:", font=("宋体", 10)).grid(row=0, column=0, sticky=tk.W, pady=5)
        nv_key_frame = ttk.Frame(nvidia_frame)
        nv_key_frame.grid(row=0, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        nv_api_key_entry = ttk.Entry(nv_key_frame, width=45, show="*")
        nv_api_key_entry.pack(side=tk.LEFT)
        nv_api_key_entry.insert(0, self.config["nvidia_api_key"])
        nv_paste_btn = ttk.Button(nv_key_frame, text="粘贴", 
                                  command=lambda: self.paste_from_clipboard(nv_api_key_entry), width=6)
        nv_paste_btn.pack(side=tk.LEFT, padx=5)
        
        nv_show_key_var = tk.BooleanVar()
        def nv_toggle_show():
            nv_api_key_entry.config(show="" if nv_show_key_var.get() else "*")
        ttk.Checkbutton(nvidia_frame, text="显示密钥", variable=nv_show_key_var, 
                       command=nv_toggle_show).grid(row=0, column=2, padx=5)
        
        ttk.Label(nvidia_frame, text="API地址:", font=("宋体", 10)).grid(row=1, column=0, sticky=tk.W, pady=5)
        nv_api_url_entry = ttk.Entry(nvidia_frame, width=50)
        nv_api_url_entry.grid(row=1, column=1, columnspan=2, sticky=tk.W, pady=5, padx=(10, 0))
        nv_api_url_entry.insert(0, self.config["nvidia_api_url"])
        
        ttk.Label(nvidia_frame, text="默认模型:", font=("宋体", 10)).grid(row=2, column=0, sticky=tk.W, pady=5)
        nv_default_model_entry = ttk.Entry(nvidia_frame, width=50)
        nv_default_model_entry.grid(row=2, column=1, columnspan=2, sticky=tk.W, pady=5, padx=(10, 0))
        nv_default_model_entry.insert(0, self.config["nvidia_model"])
        
        ttk.Label(nvidia_frame, text="💡 提示: 可在主界面工具栏下拉框中手动输入或选择模型", 
                 font=("宋体", 9), foreground="#198754").grid(row=3, column=0, columnspan=3, pady=5, sticky=tk.W)
        
        ttk.Label(nvidia_frame, text="获取密钥: build.nvidia.com", 
                 font=("宋体", 9), foreground="#6c757d").grid(row=4, column=0, columnspan=3, pady=5, sticky=tk.W)
        
        # 英伟达测试按钮放在 test_nvidia 函数定义之后
        # 见通用设置下方
        
        # === OpenAI 选项卡 ===
        openai_frame = ttk.Frame(notebook, padding=20)
        notebook.add(openai_frame, text="OpenAI")
        
        ttk.Label(openai_frame, text="API 密钥:", font=("宋体", 10)).grid(row=0, column=0, sticky=tk.W, pady=5)
        oa_key_frame = ttk.Frame(openai_frame)
        oa_key_frame.grid(row=0, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        oa_api_key_entry = ttk.Entry(oa_key_frame, width=45, show="*")
        oa_api_key_entry.pack(side=tk.LEFT)
        oa_api_key_entry.insert(0, self.config.get("openai_api_key", ""))
        oa_paste_btn = ttk.Button(oa_key_frame, text="粘贴",
                                  command=lambda: self.paste_from_clipboard(oa_api_key_entry), width=6)
        oa_paste_btn.pack(side=tk.LEFT, padx=5)
        
        oa_show_key_var = tk.BooleanVar()
        def oa_toggle_show():
            oa_api_key_entry.config(show="" if oa_show_key_var.get() else "*")
        ttk.Checkbutton(openai_frame, text="显示密钥", variable=oa_show_key_var,
                       command=oa_toggle_show).grid(row=0, column=2, padx=5)
        
        ttk.Label(openai_frame, text="API地址:", font=("宋体", 10)).grid(row=1, column=0, sticky=tk.W, pady=5)
        oa_api_url_entry = ttk.Entry(openai_frame, width=50)
        oa_api_url_entry.grid(row=1, column=1, columnspan=2, sticky=tk.W, pady=5, padx=(10, 0))
        oa_api_url_entry.insert(0, self.config.get("openai_api_url", "https://api.openai.com/v1/chat/completions"))
        
        ttk.Label(openai_frame, text="默认模型:", font=("宋体", 10)).grid(row=2, column=0, sticky=tk.W, pady=5)
        oa_model_entry = ttk.Entry(openai_frame, width=50)
        oa_model_entry.grid(row=2, column=1, columnspan=2, sticky=tk.W, pady=5, padx=(10, 0))
        oa_model_entry.insert(0, self.config.get("openai_model", "gpt-4o-mini"))
        
        ttk.Label(openai_frame, text="💡 支持任意 OpenAI 兼容 API (如 OpenAI、OpenRouter、Groq 等)", 
                 font=("宋体", 9), foreground="#198754").grid(row=3, column=0, columnspan=3, pady=5, sticky=tk.W)
        
        def test_openai():
            test_key = oa_api_key_entry.get().strip()
            test_url = oa_api_url_entry.get().strip()
            test_model = oa_model_entry.get().strip()
            if not test_key:
                messagebox.showerror("错误", "请输入 API 密钥")
                return
            try:
                headers = {
                    "Authorization": f"Bearer {test_key}",
                    "Content-Type": "application/json"
                }
                test_payload = {
                    "model": test_model if test_model else "gpt-4o-mini",
                    "messages": [{"role": "user", "content": "test"}],
                    "max_tokens": 5
                }
                response = requests.post(test_url, headers=headers, json=test_payload, timeout=10)
                if response.status_code == 200:
                    messagebox.showinfo("连接成功", "OpenAI 兼容 API 连接成功！")
                else:
                    messagebox.showerror("连接失败", f"API错误\n状态码: {response.status_code}\n{response.text[:200]}")
            except Exception as e:
                messagebox.showerror("连接失败", str(e))
        
        oa_test_btn_frame = ttk.Frame(openai_frame)
        oa_test_btn_frame.grid(row=4, column=0, columnspan=3, pady=15)
        ttk.Button(oa_test_btn_frame, text="测试 OpenAI 连接", command=test_openai).pack()

        # === 自定义模型选项卡 ===
        custom_frame = ttk.Frame(notebook, padding=20)
        notebook.add(custom_frame, text="自定义模型")
        
        ttk.Label(custom_frame, text="服务商名称:", font=("宋体", 10)).grid(row=0, column=0, sticky=tk.W, pady=5)
        custom_name_entry = ttk.Entry(custom_frame, width=50)
        custom_name_entry.grid(row=0, column=1, columnspan=2, sticky=tk.W, pady=5, padx=(10, 0))
        custom_name_entry.insert(0, self.config.get("custom_name", ""))
        ttk.Label(custom_frame, text="如: OpenRouter, Groq, SiliconFlow 等", 
                 font=("宋体", 9), foreground="#6c757d").grid(row=0, column=3, padx=5)
        
        ttk.Label(custom_frame, text="API 密钥:", font=("宋体", 10)).grid(row=1, column=0, sticky=tk.W, pady=5)
        cu_key_frame = ttk.Frame(custom_frame)
        cu_key_frame.grid(row=1, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        cu_api_key_entry = ttk.Entry(cu_key_frame, width=45, show="*")
        cu_api_key_entry.pack(side=tk.LEFT)
        cu_api_key_entry.insert(0, self.config.get("custom_api_key", ""))
        cu_paste_btn = ttk.Button(cu_key_frame, text="粘贴",
                                  command=lambda: self.paste_from_clipboard(cu_api_key_entry), width=6)
        cu_paste_btn.pack(side=tk.LEFT, padx=5)
        
        cu_show_key_var = tk.BooleanVar()
        def cu_toggle_show():
            cu_api_key_entry.config(show="" if cu_show_key_var.get() else "*")
        ttk.Checkbutton(custom_frame, text="显示密钥", variable=cu_show_key_var,
                       command=cu_toggle_show).grid(row=1, column=2, padx=5)
        
        ttk.Label(custom_frame, text="API地址:", font=("宋体", 10)).grid(row=2, column=0, sticky=tk.W, pady=5)
        cu_api_url_entry = ttk.Entry(custom_frame, width=50)
        cu_api_url_entry.grid(row=2, column=1, columnspan=2, sticky=tk.W, pady=5, padx=(10, 0))
        cu_api_url_entry.insert(0, self.config.get("custom_api_url", ""))
        ttk.Label(custom_frame, text="如: https://api.openai.com/v1/chat/completions", 
                 font=("宋体", 9), foreground="#6c757d").grid(row=2, column=3, padx=5)
        
        ttk.Label(custom_frame, text="默认模型:", font=("宋体", 10)).grid(row=3, column=0, sticky=tk.W, pady=5)
        cu_model_entry = ttk.Entry(custom_frame, width=50)
        cu_model_entry.grid(row=3, column=1, columnspan=2, sticky=tk.W, pady=5, padx=(10, 0))
        cu_model_entry.insert(0, self.config.get("custom_model", ""))
        
        ttk.Label(custom_frame, text="💡 自定义模型支持任意 OpenAI 兼容 API，填写 API 地址和密钥即可使用", 
                 font=("宋体", 9), foreground="#198754").grid(row=4, column=0, columnspan=4, pady=5, sticky=tk.W)
        
        def test_custom():
            test_key = cu_api_key_entry.get().strip()
            test_url = cu_api_url_entry.get().strip()
            test_model = cu_model_entry.get().strip()
            if not test_key or not test_url or not test_model:
                messagebox.showerror("错误", "请完整填写 API 密钥、地址和模型名称")
                return
            try:
                headers = {
                    "Authorization": f"Bearer {test_key}",
                    "Content-Type": "application/json"
                }
                test_payload = {
                    "model": test_model,
                    "messages": [{"role": "user", "content": "test"}],
                    "max_tokens": 5
                }
                response = requests.post(test_url, headers=headers, json=test_payload, timeout=10)
                if response.status_code == 200:
                    messagebox.showinfo("连接成功", f"自定义 API ({custom_name_entry.get().strip() or '未命名'}) 连接成功！")
                else:
                    messagebox.showerror("连接失败", f"API错误\n状态码: {response.status_code}\n{response.text[:200]}")
            except Exception as e:
                messagebox.showerror("连接失败", str(e))
        
        cu_test_btn_frame = ttk.Frame(custom_frame)
        cu_test_btn_frame.grid(row=5, column=0, columnspan=4, pady=15)
        ttk.Button(cu_test_btn_frame, text="测试自定义连接", command=test_custom).pack()

        # 通用设置选项卡
        general_frame = ttk.Frame(notebook, padding=20)
        notebook.add(general_frame, text="通用设置")
        
        ttk.Label(general_frame, text="当前使用:", font=("宋体", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=10)
        
        provider_var = tk.StringVar(value=self.config["provider"])
        provider_frame = ttk.Frame(general_frame)
        provider_frame.grid(row=0, column=1, sticky=tk.W, pady=10, padx=(10, 0))
        
        ttk.Radiobutton(provider_frame, text="DeepSeek", variable=provider_var, 
                       value="deepseek").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(provider_frame, text="英伟达免费模型", variable=provider_var, 
                       value="nvidia").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(provider_frame, text="OpenAI", variable=provider_var, 
                       value="openai").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(provider_frame, text="自定义模型", variable=provider_var, 
                       value="custom").pack(side=tk.LEFT, padx=10)
        
        ttk.Label(general_frame, text="Temperature:", font=("宋体", 10)).grid(row=1, column=0, sticky=tk.W, pady=10)
        temp_frame = ttk.Frame(general_frame)
        temp_frame.grid(row=1, column=1, sticky=tk.W, pady=10, padx=(10, 0))
        temp_var = tk.DoubleVar(value=self.config["temperature"])
        temp_scale = ttk.Scale(temp_frame, from_=0.0, to=1.0, variable=temp_var, orient=tk.HORIZONTAL, length=250)
        temp_scale.pack(side=tk.LEFT)
        temp_label = ttk.Label(temp_frame, text=f"{self.config['temperature']:.1f}", width=5)
        temp_label.pack(side=tk.LEFT, padx=10)
        
        def update_temp_label(*args):
            temp_label.config(text=f"{temp_var.get():.1f}")
        temp_var.trace_add('write', update_temp_label)
        
        ttk.Label(general_frame, text="最大Token数:", font=("宋体", 10)).grid(row=2, column=0, sticky=tk.W, pady=10)
        tokens_var = tk.IntVar(value=self.config["max_tokens"])
        tokens_spinbox = ttk.Spinbox(general_frame, from_=100, to=4000, textvariable=tokens_var, width=15)
        tokens_spinbox.grid(row=2, column=1, sticky=tk.W, pady=10, padx=(10, 0))
        
        ttk.Label(general_frame, text="当前Token:", font=("宋体", 10)).grid(row=3, column=0, sticky=tk.W, pady=10)
        current_token_label = ttk.Label(general_frame, text=f"今日: {self.today_tokens} | 总计: {self.total_tokens}", 
                                       font=("宋体", 10, "bold"), foreground="#0d6efd")
        current_token_label.grid(row=3, column=1, sticky=tk.W, pady=10, padx=(10, 0))
        
        def reset_token():
            if messagebox.askyesno("确认", "确定要重置Token计数吗？"):
                self.total_tokens = 0
                self.today_tokens = 0
                self.update_token_display()
                current_token_label.config(text=f"今日: 0 | 总计: 0")
                self.update_status("Token计数已重置")
        
        ttk.Button(general_frame, text="重置Token", command=reset_token, width=12).grid(row=3, column=2, pady=10)
        
        save_dir_text = f"文件保存目录: {self.save_dir}"
        ttk.Label(general_frame, text=save_dir_text, font=("宋体", 9), 
                 foreground="#0d6efd", wraplength=500).grid(row=4, column=0, columnspan=3, pady=15, sticky=tk.W)
        
        # 测试连接按钮
        def test_deepseek():
            test_key = ds_api_key_entry.get().strip()
            if not test_key:
                messagebox.showerror("错误", "请输入DeepSeek API密钥")
                return
            try:
                headers = {"Authorization": f"Bearer {test_key}"}
                response = requests.get("https://api.deepseek.com/user/balance", headers=headers, timeout=10)
                if response.status_code == 200:
                    balance = response.json()
                    balance_info = balance.get('balance', '未知')
                    if isinstance(balance_info, dict):
                        balance_info = balance_info.get('total_balance', '未知')
                    messagebox.showinfo("连接成功", f"DeepSeek API密钥有效！\n账户余额: {balance_info}")
                else:
                    messagebox.showerror("连接失败", f"API密钥无效或网络错误\n状态码: {response.status_code}")
            except Exception as e:
                messagebox.showerror("连接失败", str(e))
        
        def test_nvidia():
            test_key = nv_api_key_entry.get().strip()
            if not test_key:
                messagebox.showerror("错误", "请输入英伟达API密钥")
                return
            try:
                headers = {
                    "Authorization": f"Bearer {test_key}",
                    "Content-Type": "application/json"
                }
                test_payload = {
                    "model": nv_default_model_entry.get().strip(),
                    "messages": [{"role": "user", "content": "test"}],
                    "max_tokens": 5
                }
                response = requests.post(
                    nv_api_url_entry.get().strip(),
                    headers=headers,
                    json=test_payload,
                    timeout=30
                )
                if response.status_code == 200:
                    messagebox.showinfo("连接成功", "英伟达API密钥有效！可以开始使用免费模型。")
                else:
                    messagebox.showerror("连接失败", f"API密钥无效或网络错误\n状态码: {response.status_code}")
            except Exception as e:
                messagebox.showerror("连接失败", str(e))
        
        # 英伟达测试按钮（放在 test_nvidia 函数定义之后）
        nv_test_btn_frame = ttk.Frame(nvidia_frame)
        nv_test_btn_frame.grid(row=5, column=0, columnspan=3, pady=15)
        ttk.Button(nv_test_btn_frame, text="测试英伟达连接", command=test_nvidia).pack()
        
        ttk.Button(deepseek_frame, text="测试DeepSeek连接", command=test_deepseek).grid(row=4, column=0, columnspan=3, pady=15)
        
        button_frame = ttk.Frame(settings_window)
        button_frame.pack(fill=tk.X, pady=10, padx=20)
        
        def save_settings():
            self.config["api_key"] = ds_api_key_entry.get().strip()
            self.config["api_url"] = ds_api_url_entry.get().strip()
            self.config["model"] = ds_model_combo.get()
            self.config["nvidia_api_key"] = nv_api_key_entry.get().strip()
            self.config["nvidia_api_url"] = nv_api_url_entry.get().strip()
            self.config["nvidia_model"] = nv_default_model_entry.get().strip()
            self.config["openai_api_key"] = oa_api_key_entry.get().strip()
            self.config["openai_api_url"] = oa_api_url_entry.get().strip()
            self.config["openai_model"] = oa_model_entry.get().strip()
            self.config["custom_api_key"] = cu_api_key_entry.get().strip()
            self.config["custom_api_url"] = cu_api_url_entry.get().strip()
            self.config["custom_model"] = cu_model_entry.get().strip()
            self.config["custom_name"] = custom_name_entry.get().strip()
            self.config["provider"] = provider_var.get()
            self.config["temperature"] = temp_var.get()
            self.config["max_tokens"] = tokens_var.get()
            
            self.save_config()
            
            # 更新模型下拉列表
            self.update_model_list()
            if self.config["provider"] == "nvidia":
                self.model_combo.set(self.config["nvidia_model"])
            elif self.config["provider"] == "openai":
                self.model_combo.set(self.config["openai_model"])
            elif self.config["provider"] == "custom":
                self.model_combo.set(self.config["custom_model"])
            else:
                self.model_combo.set(self.config["model"])
            
            provider_name = self.get_provider_display_name()
            self.update_status(f"已切换到: {provider_name}")
            settings_window.destroy()
        
        ttk.Button(button_frame, text="保存设置", command=save_settings, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=settings_window.destroy, width=15).pack(side=tk.LEFT, padx=5)
    
    def show_help(self):
        help_text = f"""DeepSeek AI 助手 · 专业版  v{DeepSeekClient.VERSION:.3f}

👤 作者: 靳好宝  📧 uulov@qq.com

✨ 新功能:
• ✅ 支持英伟达免费模型，完全免费使用
• ✅ 支持 OpenAI 兼容 API (OpenAI / OpenRouter / Groq 等)
• ✅ 支持自定义模型，任意 OpenAI 兼容 API 均可接入
• ✅ Token统计: 总使用量 + 当日使用量
• ✅ 模型下拉选择，支持手动输入
• ✅ 切换服务商自动更新模型列表

快捷键:
• Ctrl+N - 新建对话
• Ctrl+S - 保存对话(TXT)
• Ctrl+C - 复制最后回复
• Ctrl+Enter - 发送消息

🤖 服务提供商:

1. DeepSeek (官方API)
   • 需要API密钥，新用户赠送5元额度
   • 获取: platform.deepseek.com

2. 英伟达免费模型 (NVIDIA)
   • 完全免费使用
   • 获取密钥: build.nvidia.com
   • 支持手动输入任意模型名称
   • 速率限制: 60请求/分钟

3. OpenAI 兼容 API
   • 支持 OpenAI 官方 (api.openai.com)
   • 支持 OpenRouter、Groq 等第三方服务
   • 支持手动输入模型名称

4. 自定义模型
   • 支持任意 OpenAI 兼容 API 服务
   • 可自定义服务商名称
   • 适合接入国内 API 代理或私有部署

📊 Token统计:
• 实时显示"今日使用量 | 总计使用量"
• 每日自动重置今日计数
• 自动保存到 token.ini 和 today_token.ini
• 可在编辑菜单重置计数

🎯 模型选择:
• 主界面工具栏右侧有模型下拉框
• DeepSeek模式: 固定模型列表
• 英伟达/OpenAI模式: 支持下拉选择或手动输入
• 自定义模式: 完全手动输入模型名称

文件保存:
• 保存目录: {self.save_dir}
• 自动保存对话历史
• 支持导出TXT/HTML格式

历史对话:
• 左侧边栏显示历史对话
• 点击加载历史对话
• 新建对话自动保存当前对话

功能说明:
1. 支持流式输出（打字机效果）
2. 可随时停止生成
3. 深色/浅色主题切换
4. 右键菜单复制功能
5. 一键粘贴API密钥
6. API连接测试

获取API密钥:
• DeepSeek: https://platform.deepseek.com
• 英伟达: https://build.nvidia.com/"""
        
        messagebox.showinfo("使用说明", help_text)
    
    def show_about(self):
        about_text = f"""DeepSeek AI 助手 · 专业版  v{DeepSeekClient.VERSION:.3f}

基于DeepSeek API和英伟达免费模型的桌面客户端

👤 作者: 靳好宝
📧 邮箱: uulov@qq.com

✨ 主要功能:
• 完整对话记忆
• 流式输出响应
• 会话历史管理
• 双服务商支持
• Token统计（总/日）
• 模型实时切换
• 深色/浅色主题

📊 Token统计:
• 总使用量: {self.total_tokens}
• 今日使用量: {self.today_tokens}

📁 文件管理:
• 保存目录: {self.save_dir}
• 历史对话自动保存
• 支持一键打开文件夹

🤖 支持的模型:
• DeepSeek: deepseek-v4-flash, deepseek-v4-pro
• 英伟达: 支持任意模型名称手动输入
• OpenAI: gpt-4o, gpt-4o-mini, 支持手动输入
• 自定义: 支持任意 OpenAI 兼容 API 服务

📦 依赖:
• Python 3.6+
• requests
• tkinter (内置)

📝 许可证: MIT"""
        
        messagebox.showinfo("关于", about_text)
    
    def load_config(self):
        """从程序目录加载配置文件"""
        config_path = os.path.join(get_program_dir(), "deepseek_config.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    saved_config = json.load(f)
                    # 版本号递增：如果保存的版本比当前类版本低且大于0，递增0.001
                    saved_ver = saved_config.get("version", 0)
                    if 0 < saved_ver < DeepSeekClient.VERSION:
                        DeepSeekClient.VERSION = round(saved_ver + 0.001, 3)
                    # 修正旧版英伟达 URL（缺少 /chat/completions）
                    if saved_config.get("nvidia_api_url") == "https://integrate.api.nvidia.com/v1":
                        saved_config["nvidia_api_url"] = "https://integrate.api.nvidia.com/v1/chat/completions"
                    # 替换已下架模型
                    if saved_config.get("nvidia_model") in ("deepseek-ai/deepseek-v3.2", "deepseek-ai/deepseek-v3.1"):
                        saved_config["nvidia_model"] = "deepseek-ai/deepseek-v4-flash"
                    self.config.update(saved_config)
                    if self.config.get("max_tokens", 2000) > 65536:
                        self.config["max_tokens"] = 4096
                    self.config["version"] = DeepSeekClient.VERSION
            else:
                # 旧版兼容：尝试从当前工作目录读取
                old_path = os.path.join(os.getcwd(), "deepseek_config.json")
                if os.path.exists(old_path):
                    with open(old_path, "r", encoding="utf-8") as f:
                        saved_config = json.load(f)
                        saved_ver = saved_config.get("version", 0)
                        if 0 < saved_ver < DeepSeekClient.VERSION:
                            DeepSeekClient.VERSION = round(saved_ver + 0.001, 3)
                        # 修正旧版英伟达 URL
                        if saved_config.get("nvidia_api_url") == "https://integrate.api.nvidia.com/v1":
                            saved_config["nvidia_api_url"] = "https://integrate.api.nvidia.com/v1/chat/completions"
                        # 替换已下架模型
                        if saved_config.get("nvidia_model") in ("deepseek-ai/deepseek-v3.2", "deepseek-ai/deepseek-v3.1"):
                            saved_config["nvidia_model"] = "deepseek-ai/deepseek-v4-flash"
                        self.config.update(saved_config)
                        if self.config.get("max_tokens", 2000) > 65536:
                            self.config["max_tokens"] = 4096
                        self.config["version"] = DeepSeekClient.VERSION
                    # 迁移到程序目录并保存修正后的配置
                    self.save_config()
        except Exception as e:
            print(f"加载配置失败: {e}")
        # 加载完后更新标题版本号
        self.root.title(f"DeepSeek AI 助手 · 专业版   v{DeepSeekClient.VERSION:.3f}  作者:靳好宝 邮箱:uulov@qq.com")
    
    def save_config(self):
        """保存配置文件到程序目录"""
        config_path = os.path.join(get_program_dir(), "deepseek_config.json")
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    style = ttk.Style()
    style.theme_use('vista')
    # 配置 Combobox 下拉样式
    style.configure("TCombobox", fieldbackground="white", background="white",
                    arrowcolor="#4B9956", font=("微软雅黑", 9))
    style.map("TCombobox", fieldbackground=[("readonly", "white")])
    # 配置进度条样式
    style.configure("TProgressbar", troughcolor="#333333", background="#add8e6",
                   bordercolor="#add8e6", lightcolor="#add8e6", darkcolor="#add8e6")
    # 配置滑动条样式
    style.configure("TScale", troughcolor="#333333", background="#add8e6")
    # 配置滚动条样式
    style.configure("Vertical.TScrollbar", troughcolor="#e0e0e0", background="#c0c0c0")
    style.configure("Accent.TButton", font=("微软雅黑", 10, "bold"))
    app = DeepSeekClient(root)
    root.mainloop()