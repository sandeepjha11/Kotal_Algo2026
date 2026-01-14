import tkinter as tk
from tkinter import messagebox

class LoginWindow(tk.Toplevel):
    def __init__(self, parent, api_handler, on_success):
        super().__init__(parent)
        self.title("Login to Kotak Neo")
        self.geometry("300x200")
        self.configure(bg="#2E2E2E")
        self.api_handler = api_handler
        self.parent = parent
        self.on_success = on_success
        self.protocol("WM_DELETE_WINDOW", self.parent.quit)

        self.create_widgets()

    def create_widgets(self):
        tk.Label(self, text="Mobile Number:", bg="#2E2E2E", fg="white").pack(pady=5)
        self.mobile_entry = tk.Entry(self)
        self.mobile_entry.pack()

        tk.Label(self, text="Password:", bg="#2E2E2E", fg="white").pack(pady=5)
        self.password_entry = tk.Entry(self, show="*")
        self.password_entry.pack()

        tk.Label(self, text="MPIN:", bg="#2E2E2E", fg="white").pack(pady=5)
        self.mpin_entry = tk.Entry(self, show="*")
        self.mpin_entry.pack()

        login_button = tk.Button(self, text="Login", command=self.attempt_login)
        login_button.pack(pady=10)

    def attempt_login(self):
        mobile = self.mobile_entry.get()
        password = self.password_entry.get()
        mpin = self.mpin_entry.get()

        if not all([mobile, password, mpin]):
            messagebox.showerror("Error", "All fields are required.")
            return

        is_successful = self.api_handler.login(mobile, password, mpin)

        if is_successful:
            self.destroy() # Close the login window
            self.on_success() # Call the success callback
        else:
            messagebox.showerror("Login Failed", "Invalid credentials. Please try again.")
