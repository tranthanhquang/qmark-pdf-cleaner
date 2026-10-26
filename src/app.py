"""Tkinter desktop workflow for local scan-marker removal."""

from __future__ import annotations

import base64
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .pdf_markers import (
    PDFProcessingError,
    ProcessingResult,
    render_page_preview,
    save_cleaned_pdf,
    scan_pdf,
)


class MarkerRemovalApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("QMark PDF Cleaner")
        self.geometry("900x900")
        self.result: ProcessingResult | None = None
        self.candidate_pages: list[int] = []
        self.current_candidate = 0
        self.photo = None

        toolbar = ttk.Frame(self, padding=10)
        toolbar.pack(fill="x")
        ttk.Button(toolbar, text="Open PDF", command=self.open_pdf).pack(side="left")
        ttk.Button(toolbar, text="Save reviewed copy", command=self.save_pdf).pack(
            side="left", padx=8
        )
        ttk.Button(toolbar, text="Cancel", command=self.cancel).pack(side="left")
        self.status = tk.StringVar(value="Files are processed only on this device.")
        ttk.Label(self, textvariable=self.status, padding=(10, 0)).pack(fill="x")

        navigation = ttk.Frame(self, padding=10)
        navigation.pack(fill="x")
        ttk.Button(navigation, text="Previous", command=self.previous_page).pack(
            side="left"
        )
        ttk.Button(navigation, text="Next", command=self.next_page).pack(
            side="left", padx=8
        )
        self.page_label = tk.StringVar(value="No PDF selected")
        ttk.Label(navigation, textvariable=self.page_label).pack(side="left", padx=8)
        self.remove_var = tk.BooleanVar(value=False)
        self.remove_toggle = ttk.Checkbutton(
            navigation,
            text="Remove mark from this page",
            variable=self.remove_var,
            command=self.update_page_choice,
        )
        self.remove_toggle.pack(side="right")

        preview = ttk.Frame(self, padding=(10, 0, 10, 10))
        preview.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(preview, background="#dddddd", highlightthickness=0)
        vertical_scroll = ttk.Scrollbar(preview, orient="vertical", command=self.canvas.yview)
        horizontal_scroll = ttk.Scrollbar(
            preview, orient="horizontal", command=self.canvas.xview
        )
        self.canvas.configure(
            yscrollcommand=vertical_scroll.set, xscrollcommand=horizontal_scroll.set
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        vertical_scroll.grid(row=0, column=1, sticky="ns")
        horizontal_scroll.grid(row=1, column=0, sticky="ew")
        preview.rowconfigure(0, weight=1)
        preview.columnconfigure(0, weight=1)

    def open_pdf(self):
        path = filedialog.askopenfilename(
            title="Select a PDF", filetypes=[("PDF files", "*.pdf")]
        )
        if not path:
            return
        if not messagebox.askyesno(
            "Permission to modify",
            "Confirm that you own this PDF or have permission to modify it.",
        ):
            return

        self.status.set("Scanning locally for the supported scan mark...")
        self.update_idletasks()
        try:
            result = scan_pdf(path)
        except PDFProcessingError as exc:
            self.status.set("No PDF is being processed.")
            messagebox.showerror("Cannot process PDF", str(exc))
            return

        self.result = result
        self.candidate_pages = [
            index for index, review in enumerate(result.pages) if review.candidates
        ]
        if not self.candidate_pages:
            self.page_label.set("No supported mark found")
            self.status.set(
                f"Scanned {result.page_count} pages. "
                f"No supported mark found in {Path(path).name}."
            )
            self.canvas.delete("all")
            messagebox.showinfo("No mark found", "No supported scan mark was found.")
            return

        self.current_candidate = 0
        self.show_current_page()
        self.status.set(
            f"Scanned {result.page_count} pages; found mark candidates on "
            f"{len(self.candidate_pages)} page(s). Review before saving."
        )

    def show_current_page(self):
        if not self.result or not self.candidate_pages:
            return
        page_index = self.candidate_pages[self.current_candidate]
        review = self.result.pages[page_index]
        try:
            png = render_page_preview(self.result, review.page_number)
        except PDFProcessingError as exc:
            messagebox.showerror("Cannot preview PDF", str(exc))
            return
        self.photo = tk.PhotoImage(data=base64.b64encode(png).decode("ascii"))
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.photo)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.page_label.set(
            f"PDF page {review.page_number} of {self.result.page_count} - candidate "
            f"{self.current_candidate + 1} of {len(self.candidate_pages)}"
        )
        self.remove_var.set(review.remove)

    def update_page_choice(self):
        if self.result and self.candidate_pages:
            page_index = self.candidate_pages[self.current_candidate]
            self.result.pages[page_index].remove = self.remove_var.get()

    def previous_page(self):
        if self.candidate_pages:
            self.update_page_choice()
            self.current_candidate = (self.current_candidate - 1) % len(self.candidate_pages)
            self.show_current_page()

    def next_page(self):
        if self.candidate_pages:
            self.update_page_choice()
            self.current_candidate = (self.current_candidate + 1) % len(self.candidate_pages)
            self.show_current_page()

    def save_pdf(self):
        if not self.result or not self.candidate_pages:
            messagebox.showinfo("No changes", "Open a PDF with a supported mark first.")
            return
        self.update_page_choice()
        destination = filedialog.asksaveasfilename(
            title="Save cleaned PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
        )
        if not destination:
            return
        source = self.result.source_path.resolve()
        target = Path(destination).expanduser().resolve()
        if source == target:
            messagebox.showerror("Cannot overwrite source", "Choose a different output file.")
            return
        if target.exists() and not messagebox.askyesno(
            "Replace output", f"Replace the existing file {target.name}?"
        ):
            return

        if not messagebox.askyesno(
            "Accept changes",
            "Save the reviewed choices to a separate PDF? Removed regions will be blank; hidden content is not restored.",
        ):
            return
        try:
            saved = save_cleaned_pdf(self.result, target)
        except PDFProcessingError as exc:
            self.status.set("No completed output was saved.")
            messagebox.showerror("Cannot save PDF", str(exc))
            return
        self.status.set(f"Saved cleaned PDF: {saved}")
        messagebox.showinfo("PDF saved", f"Saved cleaned PDF to:\n{saved}")

    def cancel(self):
        self.result = None
        self.candidate_pages = []
        self.current_candidate = 0
        self.canvas.delete("all")
        self.page_label.set("No PDF selected")
        self.status.set("Review cancelled. No output was created.")


def main():
    MarkerRemovalApp().mainloop()
