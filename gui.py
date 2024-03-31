import re
import tkinter as tk

from main import main
from utils import Record
from enums import LinkType, PublishedOptions, PublishedCustomOptions

default_bg_style = {
    "bg": "#ffffff",
}

default_font = ("Arial", 9, "bold")

default_style = {
    **default_bg_style,
    "fg": "#333333",
    "font": default_font,
}


frame_style = {
    **default_style,
    "relief": "groove",
    "padx": 20,
    "pady": 20,
}


class App(tk.Tk):

    def __init__(self, *args, **kwargs):

        tk.Tk.__init__(self, *args, **kwargs)
        main = tk.Frame(self, bg="#ffffff", height=700, width=1400, padx=20, pady=20)
        main.pack(fill="both", expand="true")
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=2)

        self.config = {
            "query": tk.StringVar(value="{...} type beat"),
            "type": [
                tk.BooleanVar(value=True if t.value == "email" else False)
                for t in LinkType
            ],
            "max": tk.IntVar(value=20),
            "published_mode": tk.StringVar(value="last_week"),
            "published_custom": [tk.IntVar() for _ in PublishedCustomOptions],
        }

        self.create_search(main)
        self.create_output(main)

        self.resizable(0, 0)
        self.geometry("1024x600")
        tk.Tk.config(self)

    def trigger_search(self):
        print("Searching...")

        q = self.config["query"].get()
        q = re.sub("[\s+]", "", q)
        q = q.split(",")

        print(q)
        print(self.config)

        config = Record(
            q=q,
            type=[
                list(LinkType)[i].value
                for i, var in enumerate(self.config["type"])
                if var.get()
            ],
            max=self.config["max"].get(),
            published_mode=self.config["published_mode"].get(),
            published_custom=[var.get() for var in self.config["published_custom"]],
        )
        main(config)

    def attach_color_cb(self, elt, var, active_val):
        def wrapper(elt, var):
            def on_change(*args):
                color = "#C3FFD5" if var.get() == active_val else "#ffffff"
                elt["bg"] = color
                elt["activebackground"] = color

            return on_change

        command = wrapper(elt, var)
        elt["command"] = command
        command()

    def attach_color_cb_list(self, elts_active_vals, var):
        def on_change(*args):
            for elt, active_val in elts_active_vals:
                color = "#C3FFD5" if var.get() == active_val else "#ffffff"
                elt["bg"] = color
                elt["activebackground"] = color

        var.trace("w", on_change)
        on_change()

    def create_published_frame(self, search_frame):
        parent = tk.Frame(
            search_frame,
            default_bg_style,
            relief="flat",
            borderwidth=20,
        )
        parent.pack(fill="x")

        publish_mode_frame = tk.LabelFrame(
            parent,
            default_style,
            text="Published after",
            relief="flat",
        )
        publish_mode_frame.grid(row=0, column=0, sticky=tk.W)

        radios = []
        for i, opt in enumerate(PublishedOptions):
            radio = tk.Radiobutton(
                publish_mode_frame,
                text=opt.value,
                variable=self.config["published_mode"],
                value=opt.value,
                bg="#ffffff",
                padx=10,
            )
            radio.grid(column=i, row=0, ipadx=5, ipady=5)
            radios.append((radio, opt.value))

        self.attach_color_cb_list(radios, self.config["published_mode"])

        publish_custom_frame = tk.Frame(
            parent,
            default_bg_style,
            relief="flat",
        )

        for i, opt in enumerate(PublishedCustomOptions):
            frame = tk.LabelFrame(
                publish_custom_frame,
                default_style,
                text=opt.name.lower(),
                relief="flat",
                padx=5,
                pady=5,
            )
            frame.grid(row=0, column=i, sticky=tk.W)

            spinbox = tk.Spinbox(
                frame,
                from_=0,
                to=99,
                textvariable=self.config["published_custom"][i],
            )
            spinbox.pack()

        def on_publish_mode_change(*args):
            if self.config["published_mode"].get() == PublishedOptions.CUSTOM.value:
                publish_custom_frame.grid(row=1, column=0, sticky=tk.W)
            else:
                publish_custom_frame.grid_forget()

        self.config["published_mode"].trace("w", on_publish_mode_change)

    def create_search(self, main):
        search_frame = tk.LabelFrame(main, frame_style, text="Search")
        search_frame.grid(row=0, column=0, sticky=tk.NSEW)

        query_frame = tk.LabelFrame(
            search_frame, default_style, text="Query", relief="flat", borderwidth=20
        )
        query_frame.pack(fill="x")

        query_entry = tk.Entry(
            query_frame,
            textvariable=self.config["query"],
            borderwidth=10,
            relief=tk.FLAT,
        )
        query_entry.pack(fill="x")

        type_frame = tk.LabelFrame(
            search_frame, default_style, text="Type", relief="flat", borderwidth=20
        )
        type_frame.pack(fill="x")

        for i, (opt, var) in enumerate(zip(LinkType, self.config["type"])):
            cb = tk.Checkbutton(
                type_frame,
                text=opt.name.lower(),
                variable=var,
                onvalue=True,
                offvalue=False,
                bg="#ffffff",
                padx=10,
            )
            self.attach_color_cb(cb, var, True)
            cb.grid(column=i, row=0, ipadx=5, ipady=5)
            if var.get():
                cb.select()

        self.create_published_frame(search_frame)

        max_frame = tk.LabelFrame(
            search_frame,
            default_style,
            text="Max Results (per query artist)",
            relief="flat",
            borderwidth=20,
        )
        max_frame.pack(fill="x")

        max_spinbox = tk.Spinbox(
            max_frame,
            from_=1,
            to=500,
            increment=10,
            textvariable=self.config["max"],
            relief="flat",
            borderwidth=5,
        )
        max_spinbox.pack(fill="x")

        search_button = tk.Button(
            search_frame, text="Search", command=self.trigger_search, relief="flat"
        )
        search_button.pack()

    def create_output(self, main):
        output_frame = tk.LabelFrame(main, frame_style, text="Output")
        output_frame.grid(row=0, column=1, sticky=tk.NSEW)

        """output_frame = tk.LabelFrame(self, frame_styles, text="Output")
        output_frame.place(rely=0.05, relx=0.45, height=500, width=500)

        # This is a treeview.
        tv1 = ttk.Treeview(output_frame)
        column_list_account = ["Name", "Type", "Base Stat Total"]
        tv1["columns"] = column_list_account
        tv1["show"] = "headings"  # removes empty column
        for column in column_list_account:
            tv1.heading(column, text=column)
            tv1.column(column, width=50)
        tv1.place(relheight=1, relwidth=0.995)
        treescroll = tk.Scrollbar(output_frame)
        treescroll.configure(command=tv1.yview)
        tv1.configure(yscrollcommand=treescroll.set)
        treescroll.pack(side="right", fill="y")

        def Load_data():
            for row in [
                ["Bulbasaur", "Grass", 318],
                ["Ivysaur", "Grass", 405],
                ["Venusaur", "Grass", 525],
            ]:
                tv1.insert("", "end", values=row)

        def Refresh_data():
            # Deletes the data in the current treeview and reinserts it.
            tv1.delete(*tv1.get_children())  # *=splat operator
            Load_data()

        Load_data()"""


if __name__ == "__main__":
    root = App()
    root.title("yt-desc-parser")
    root.mainloop()
