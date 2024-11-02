import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
from datetime import datetime
from network import MessengerClient

class ModernTheme:
    BG_COLOR = "#2C2F33"
    TEXT_COLOR = "#FFFFFF"
    INPUT_BG = "#40444B"
    ACCENT_COLOR = "#7289DA"
    CHAT_BG = "#36393F"
    FONT = ("Helvetica", 10)
    MESSAGE_PADDING = 8

class MessengerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Modern Messenger")
        self.root.geometry("800x600")
        self.root.configure(bg=ModernTheme.BG_COLOR)
        
        # Configure custom styles
        self.setup_styles()
        self.setup_gui()
        self.client = None
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_styles(self):
        style = ttk.Style()
        style.configure('Modern.TFrame', background=ModernTheme.BG_COLOR)
        style.configure('Modern.TButton',
            background=ModernTheme.ACCENT_COLOR,
            foreground=ModernTheme.TEXT_COLOR,
            padding=10,
            font=ModernTheme.FONT)
        style.configure('Modern.TEntry',
            fieldbackground=ModernTheme.INPUT_BG,
            foreground=ModernTheme.TEXT_COLOR,
            padding=8)
        style.map('Modern.TButton',
            background=[('active', ModernTheme.ACCENT_COLOR)],
            foreground=[('active', ModernTheme.TEXT_COLOR)])

    def setup_gui(self):
        # Main container
        main_container = ttk.Frame(self.root, style='Modern.TFrame', padding="20")
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Header
        header = ttk.Frame(main_container, style='Modern.TFrame')
        header.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        header_label = tk.Label(header, 
            text="Modern Messenger",
            font=("Helvetica", 16, "bold"),
            bg=ModernTheme.BG_COLOR,
            fg=ModernTheme.TEXT_COLOR)
        header_label.pack(side=tk.LEFT)

        # Chat area with custom styling
        chat_frame = ttk.Frame(main_container, style='Modern.TFrame')
        chat_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.chat_area = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            font=ModernTheme.FONT,
            bg=ModernTheme.CHAT_BG,
            fg=ModernTheme.TEXT_COLOR,
            insertbackground=ModernTheme.TEXT_COLOR,
            selectbackground=ModernTheme.ACCENT_COLOR,
            padx=10,
            pady=10
        )
        self.chat_area.pack(fill=tk.BOTH, expand=True)
        self.chat_area.config(state='disabled')

        # Message input area
        input_frame = ttk.Frame(main_container, style='Modern.TFrame')
        input_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        input_frame.columnconfigure(0, weight=1)

        self.message_var = tk.StringVar()
        self.message_entry = ttk.Entry(
            input_frame,
            textvariable=self.message_var,
            style='Modern.TEntry',
            font=ModernTheme.FONT
        )
        self.message_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        self.message_entry.bind('<Return>', lambda e: self.send_message())

        # Send button with modern styling
        send_button = ttk.Button(
            input_frame,
            text="Send",
            style='Modern.TButton',
            command=self.send_message
        )
        send_button.grid(row=0, column=1)

        # Configure grid weights
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(1, weight=1)

    def format_message(self, message):
        return f"{message}\n"

    def connect_to_server(self, username, host='localhost', port=5000):
        try:
            self.client = MessengerClient(username, host, port)
            if not self.client.connect():
                messagebox.showerror("Connection Error", "Could not connect to server")
                self.root.quit()
                return False
            
            self.client.on_message = self.display_message
            
            # Start receiving messages
            receive_thread = threading.Thread(target=self.client.receive_messages)
            receive_thread.daemon = True
            receive_thread.start()
            
            # Update header with connection info
            self.display_system_message(f"Connected as {username}")
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Connection error: {str(e)}")
            self.root.quit()
            return False

    def send_message(self):
        message = self.message_var.get().strip()
        if message and self.client:
            try:
                self.client.send_message(message)
                self.message_var.set("")
                self.message_entry.focus()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to send message: {str(e)}")

    def display_message(self, message):
        try:
            self.chat_area.config(state='normal')
            formatted_message = self.format_message(message)
            self.chat_area.insert(tk.END, formatted_message)
            self.chat_area.see(tk.END)
            self.chat_area.config(state='disabled')
        except Exception as e:
            print(f"Error displaying message: {str(e)}")

    def display_system_message(self, message):
        try:
            self.chat_area.config(state='normal')
            system_message = f"System: {message}\n"
            self.chat_area.insert(tk.END, system_message, 'system')
            self.chat_area.tag_configure('system', foreground='#95a5a6')
            self.chat_area.see(tk.END)
            self.chat_area.config(state='disabled')
        except Exception as e:
            print(f"Error displaying system message: {str(e)}")

    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            if self.client:
                self.client.close()
            self.root.destroy()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = MessengerGUI()
    username = input("Enter your username: ")
    if app.connect_to_server(username):
        app.run()