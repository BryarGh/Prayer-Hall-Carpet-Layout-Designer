import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.pyplot as plt

##########################
# Utility / Parsing
##########################

def circumference_to_radius(circum_m):
    """Convert a column circumference to radius in meters."""
    return float(circum_m) / (2.0 * np.pi)

def parse_columns(txt):
    """
    Parse multiline text of columns.
    Format per line: label, x_center, y_center, circumference
    Example:
        C2, 5.95, 2.91, 1.23
    Return list of (label, cx, cy, radius).
    """
    lines = txt.strip().splitlines()
    columns = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(',')]
        if len(parts) < 4:
            raise ValueError(f"Invalid column line: '{line}'")
        lbl, sx, sy, scirc = parts
        cx = float(sx)
        cy = float(sy)
        c_circ = float(scirc)
        cr = circumference_to_radius(c_circ)
        columns.append((lbl, cx, cy, cr))
    return columns

def parse_forced_rows(txt):
    """
    Parse forced row heights from multiline text.
    Each line: row_index, row_height
    e.g. 3, 0.66
    Return dict {row_index: forced_height}.
    """
    lines = txt.strip().splitlines()
    out = {}
    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(',')]
        if len(parts) < 2:
            raise ValueError(f"Invalid forced row line: '{line}'")
        i = int(parts[0])
        h = float(parts[1])
        out[i] = h
    return out

###########################
# Row-Building Logic
###########################

def build_rows(total_length, default_height, forced_heights):
    """
    From y=0 to y=<total_length>, stacking rows.
    If row_index is in forced_heights, use that. Else use default_height.
    Stop if we exceed total_length (clamp last row).
    Return list of (row_index, y_start, y_end).
    """
    rows = []
    cur_y = 0.0
    i = 1
    while True:
        if cur_y >= total_length:
            break
        forced_h = forced_heights.get(i, default_height)
        y_end = cur_y + forced_h
        if y_end > total_length:
            y_end = total_length
        rows.append((i, cur_y, y_end))
        cur_y = y_end
        i += 1
        if cur_y >= total_length:
            break
    return rows

###########################
# Visualization
###########################

def plot_prayer_hall(ax, rows, hall_width, columns, columns_to_ignore):
    """
    Draw the layout:
    - full row width = hall_width
    - color rows orange if any non-ignored column intrudes.
    - columns as red circles.
    """
    def in_band(cy, ystart, yend):
        return (cy >= ystart) and (cy < yend)

    # separate columns that affect custom logic
    custom_cols = [(lbl, cx, cy, cr) for (lbl, cx, cy, cr) in columns
                   if lbl not in columns_to_ignore]

    # Mark each row
    row_data = []
    for (idx, ys, ye) in rows:
        row_cols = []
        for (lbl, cx, cy, cr) in custom_cols:
            if in_band(cy, ys, ye):
                row_cols.append((lbl, cx, cy, cr))
        is_custom = bool(row_cols)
        row_data.append((idx, ys, ye, is_custom, row_cols))

    ax.clear()

    # draw each row
    for (i, ys, ye, is_custom, row_cols) in row_data:
        row_height = ye - ys
        color = 'orange' if is_custom else 'green'
        ax.add_patch(
            plt.Rectangle((0, ys), hall_width, row_height,
                          facecolor=color, alpha=0.3, edgecolor='black')
        )
        label_y = ys + row_height * 0.5
        ax.text(hall_width*0.5, label_y,
                f"R{i}\nH={row_height:.2f}m\n{'Custom' if is_custom else 'Normal'}",
                ha='center', va='center', fontsize=8)

    # draw columns
    for (lbl, cx, cy, cr) in columns:
        circ = plt.Circle((cx, cy), cr, color='red', alpha=0.6)
        ax.add_patch(circ)
        ax.text(cx, cy, lbl, color='black', fontsize=7,
                ha='center', va='center')

    # invert y-axis so front=0 is top
    y_max = rows[-1][2] if rows else 0
    ax.set_xlim(0, hall_width)
    ax.set_ylim(y_max, 0)
    ax.set_aspect('equal', adjustable='box')
    ax.set_xlabel(f"X=0 to X={hall_width}")
    ax.set_ylabel(f"Y=0 (Front) to Y={y_max:.2f} (Back)")
    ax.set_title("Prayer Hall Layout (Forcing Row Heights)")

    ax.figure.canvas.draw()

    # Also print a console summary
    print("\n--- Row Summary ---")
    for (i, ys, ye, is_custom, row_cols) in row_data:
        row_h = ye - ys
        row_type = "Custom" if is_custom else "Normal"
        print(f"\nRow {i}: y=[{ys:.2f},{ye:.2f}], height={row_h:.2f}, {row_type}")
        if not is_custom:
            print(f" => Normal row => {hall_width:.2f}m x {row_h:.2f}m")
        else:
            # compute horizontal cut intervals
            cuts = []
            for (lbl, cx, cy, cr) in row_cols:
                x_min = cx - cr
                x_max = cx + cr
                # clamp
                if x_min < 0: x_min = 0
                if x_max > hall_width: x_max = hall_width
                if x_max > x_min:
                    cuts.append((x_min, x_max))
            cuts.sort(key=lambda x: x[0])
            merged = []
            for iv in cuts:
                if not merged:
                    merged.append(iv)
                else:
                    prev = merged[-1]
                    if iv[0] <= prev[1]:
                        merged[-1] = (prev[0], max(prev[1], iv[1]))
                    else:
                        merged.append(iv)
            # leftover segments
            leftover = []
            start_x = 0.0
            for (cstart, cend) in merged:
                if cstart > start_x:
                    leftover.append((start_x, cstart))
                start_x = cend
            if start_x < hall_width:
                leftover.append((start_x, hall_width))
            print(f" => Columns: {[c[0] for c in row_cols]}")
            print(f" => Full row: {hall_width:.2f} x {row_h:.2f}, cut intervals: {merged}")
            if leftover:
                for seg in leftover:
                    sw = seg[1] - seg[0]
                    print(f"    leftover x=[{seg[0]:.2f},{seg[1]:.2f}] => width={sw:.2f}m")

############################
# The GUI App
############################

class ForcedHeightGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Prayer Hall Layout (Forced Row Heights)")
        self.geometry("900x700")

        # top controls
        ctrl_frame = ttk.Frame(self)
        ctrl_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        # row 1: length, width
        ttk.Label(ctrl_frame, text="Hall Length (m):").grid(row=0, column=0, sticky="e")
        self.length_var = tk.StringVar(value="16.15")
        ttk.Entry(ctrl_frame, textvariable=self.length_var, width=7).grid(row=0, column=1, sticky="w")

        ttk.Label(ctrl_frame, text="Hall Width (m):").grid(row=0, column=2, sticky="e")
        self.width_var = tk.StringVar(value="17.37")
        ttk.Entry(ctrl_frame, textvariable=self.width_var, width=7).grid(row=0, column=3, sticky="w")

        # row 2: default row height
        ttk.Label(ctrl_frame, text="Default Row Height (m):").grid(row=1, column=0, sticky="e")
        self.def_h_var = tk.StringVar(value="1.35")
        ttk.Entry(ctrl_frame, textvariable=self.def_h_var, width=7).grid(row=1, column=1, sticky="w")

        # row 2 continued: forced row heights text
        ttk.Label(ctrl_frame, text="Forced Row Heights:\n(row_i, height)").grid(row=1, column=2, sticky="ne")
        self.forced_text = tk.Text(ctrl_frame, width=20, height=4)
        self.forced_text.grid(row=1, column=3, sticky="w", padx=5)
        # example forced lines
        example_forced = "3, 0.66\n7, 0.66\n11, 0.66"
        self.forced_text.insert("1.0", example_forced)

        # row 3: columns data
        ttk.Label(ctrl_frame, text="Columns (label,x,y,circumf):").grid(row=2, column=0, sticky="ne")
        self.col_text = tk.Text(ctrl_frame, width=40, height=6)
        self.col_text.grid(row=2, column=1, columnspan=3, sticky="w", padx=5, pady=5)
        sample_cols = (
            "C1, 2.4, 2.0, 0.8\n"
            "C2, 5.95, 2.91, 1.23\n"
            "C3, 11.95, 2.98, 1.2\n"
            "C4, 13.12, 7.57, 1.51\n"
            "C5, 12.97, 12.5, 1.58\n"
        )
        self.col_text.insert("1.0", sample_cols)

        # row 4: buttons
        btn_frame = ttk.Frame(ctrl_frame)
        btn_frame.grid(row=3, column=0, columnspan=4, pady=5)
        ttk.Button(btn_frame, text="Plot Layout", command=self.on_plot).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Quit", command=self.destroy).grid(row=0, column=1, padx=5)

        # figure/canvas
        self.fig = plt.Figure(figsize=(6,5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # add toolbar
        self.toolbar = NavigationToolbar2Tk(self.canvas, self)
        self.toolbar.update()
        self.canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def on_plot(self):
        try:
            # get user input
            L = float(self.length_var.get())
            W = float(self.width_var.get())
            def_h = float(self.def_h_var.get())

            forced_str = self.forced_text.get("1.0", "end")
            forced_heights = parse_forced_rows(forced_str)

            col_str = self.col_text.get("1.0", "end")
            columns = parse_columns(col_str)

            # build rows
            rows = build_rows(L, def_h, forced_heights)

            # ignore C1 in marking custom
            columns_to_ignore = {"C1"}

            # plot
            plot_prayer_hall(self.ax, rows, W, columns, columns_to_ignore)

            self.canvas.draw()
            self.toolbar.update()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to plot:\n{e}")


def main():
    app = ForcedHeightGUI()
    app.mainloop()

if __name__ == "__main__":
    main()

