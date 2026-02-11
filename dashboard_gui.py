import json
import os
import tkinter as tk


def load_perf():
    path = os.path.join("output", "performance.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    root = tk.Tk()
    root.title("Quant Monitor")

    text = tk.Text(root, width=80, height=20)
    text.pack()

    def refresh():
        perf = load_perf()
        text.delete("1.0", tk.END)
        for k, v in perf.items():
            text.insert(tk.END, f"{k}: {v}\n")
        root.after(1000, refresh)

    refresh()
    root.mainloop()


if __name__ == "__main__":
    main()
