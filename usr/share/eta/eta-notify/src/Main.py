#!/usr/bin/env python3

import os
import argparse
import gi
import shutil
import re
import json

gi.require_version("Gtk", "3.0")
gi.require_version("WebKit2", "4.1")

from gi.repository import Gtk, WebKit2, Pango, Gdk, GLib

class HtmlViewer(Gtk.Window):
    def __init__(self, file_path=None, show_close_button=False, full_screen=False, url=None, text=None, text_size=14, show_titlebar=False, timeout=None):
        super().__init__(title="ETA BİLDİRİM")
        self.set_default_size(800, 600)

        # Center the window on the screen
        self.set_position(Gtk.WindowPosition.CENTER)

        # Set the window bar (title bar) based on the parameter
        self.set_decorated(show_titlebar)

        overlay = Gtk.Overlay()
        vbox = Gtk.VBox()

        if text:
            label = Gtk.Label()
            label.set_text(text)
            label.set_line_wrap(True)
            label.set_selectable(False)
            label.set_margin_top(15)
            label.set_margin_bottom(15)
            label.set_margin_start(15)
            label.set_margin_end(15)
            label.set_name("custom_label")
            
            scrolled_window = Gtk.ScrolledWindow()
            scrolled_window.set_margin_top(15)
            scrolled_window.set_margin_bottom(15)
            scrolled_window.set_margin_start(15)
            scrolled_window.set_margin_end(15)
            scrolled_window.add(label)
            vbox.pack_start(scrolled_window, True, True, 0)
            
            css_provider = Gtk.CssProvider()
            css_provider.load_from_data(f"""
            #custom_label {{
                font-size: {text_size}pt;
            }}
            """.encode())
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(),
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        else:
            webview = WebKit2.WebView()
            if url:
                webview.load_uri(url)
            elif file_path:
                webview.load_uri("file://" + file_path)
            scrolled_window = Gtk.ScrolledWindow()
            scrolled_window.add(webview)
            vbox.pack_start(scrolled_window, True, True, 0)

        overlay.add(vbox)

        if show_close_button:
            close_button = Gtk.Button()
            close_button_image = Gtk.Image.new_from_icon_name(
                "window-close-symbolic", Gtk.IconSize.LARGE_TOOLBAR
            )
            close_button.add(close_button_image)
            close_button.get_style_context().add_class("destructive-action")
            close_button.connect("clicked", Gtk.main_quit)
            overlay.add_overlay(close_button)
            close_button.set_halign(Gtk.Align.START)
            close_button.set_valign(Gtk.Align.END)
            close_button.set_margin_bottom(15)
            close_button.set_margin_start(15)

        self.add(overlay)
        self.connect("destroy", Gtk.main_quit)
        self.show_all()

        if full_screen:
            self.fullscreen()

        # Set up auto-close timeout if specified
        if timeout:
            GLib.timeout_add_seconds(timeout, self.close_window)

    def close_window(self):
        """Close the window and quit the application."""
        self.close()
        Gtk.main_quit()

def main():
    parser = argparse.ArgumentParser(
        description="CLI Based Notifier for ETAP",
        usage=argparse.SUPPRESS,
        formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=35, width=100)
    )

    # Grup 1: File / URL
    group1 = parser.add_argument_group("File/URL")
    group1.add_argument("--file", type=str, help="Set the html file path")
    group1.add_argument("--url", type=str, help="Set the url")

    # Grup 2: Text
    group2 = parser.add_argument_group("Text")
    group2.add_argument("--text", type=str, help="Set the text to show")
    group2.add_argument("--text-size", type=int, default=14, help="Set the text size")

    # Grup 3: Temp
    group3 = parser.add_argument_group("Template")
    group3.add_argument("--temp", type=int, help="Select the temp (e.g., 1 for temp1/index.html)")
    group3.add_argument("--temp-text", type=str, help="Set the Text data to show for temp")
    group3.add_argument("--temp-json", type=str, help="Set the JSON data to show for temp")

    # Grup 4: Display Options
    group4 = parser.add_argument_group("Display Options")
    group4.add_argument("--timeout", type=int, help="Set the timeout (in seconds) for auto-close")
    group4.add_argument("--show-close-button", action="store_true", help="Show close button")
    group4.add_argument("--full-screen", action="store_true", help="Show in full screen")
    group4.add_argument("--titlebar", action="store_true", help="Show the window title bar")
    

    args = parser.parse_args()

    # Handle the --temp argument
    if args.temp:
        original_folder_path = os.path.dirname(os.path.abspath(__file__)) + f"/../data/temp{args.temp}"
        new_folder_path = os.path.abspath(f"/tmp/temp{args.temp}")

        # Copy the template file to a .ini file with force overwrite
        if os.path.exists(new_folder_path):
            shutil.rmtree(new_folder_path)
        shutil.copytree(original_folder_path, new_folder_path, dirs_exist_ok=True)

        modified_file_path = os.path.join(new_folder_path, "index.html")

        # Handle --temp-text
        if args.temp_text:
            with open(modified_file_path, "r") as file:
                content = file.read()

            pattern = r'@([TVIY])\((.*?)\)'
            tags = {'T': 'p', 'V': 'iframe', 'I': 'img', 'Y': 'youtube'}

            html_parts = []
            for match in re.finditer(pattern, args.temp_text):
                tag_type, value = match.groups()
                if tag_type == 'T':
                    html_value = value.replace('\n', '<br>')
                    html_parts.append(f"<tr><td><p>{html_value}</p></td></tr>")
                elif tag_type == 'V':
                    html_parts.append(f'<tr><td><iframe width="560" height="315" src="{value}" frameborder="0" allowfullscreen></iframe></td></tr>')
                elif tag_type == 'I':
                    html_parts.append(f'<tr><td><img src="{value}" alt="image"></td></tr>')
                elif tag_type == 'Y':
                    video_id_match = re.search(r'(?:v=|youtu\.be/)([\w\-]+)', value)
                    if video_id_match:
                        video_id = video_id_match.group(1)
                        embed_url = f"https://www.youtube.com/embed/{video_id}"
                        html_parts.append(f'<tr><td><iframe width="560" height="315" src="{embed_url}" frameborder="0" allowfullscreen></iframe></td></tr>')

            final_html = "\n".join(html_parts)
            content = content.replace("@MESSAGE@", final_html)

            with open(modified_file_path, "w") as file:
                file.write(content)

        # Handle --temp-json
        if args.temp_json:
            with open(modified_file_path, "r") as file:
                content = file.read()

            try:
                json_data = json.loads(args.temp_json)
                html_parts = []
                for item in json_data:
                    if item["type"] == "text":
                        html_parts.append(f"<tr><td><p style='font-size: {args.text_size}px'>{item['content'].replace(chr(10), '<br>')}</p></td></tr>")
                    elif item["type"] == "image":
                        html_parts.append(f'<tr><td><img src="{item["src"]}" alt="image"></td></tr>')
                    elif item["type"] == "video":
                        html_parts.append(f'<tr><td><iframe width="560" height="315" src="{item["src"]}" frameborder="0" allowfullscreen></iframe></td></tr>')
                    elif item["type"] == "youtube":
                        video_id_match = re.search(r'(?:v=|youtu.be/|youtube.com/watch\?v=)([\w-]+)', item["src"])
                        if video_id_match:
                            video_id = video_id_match.group(1)
                            embed_url = f"https://www.youtube.com/embed/{video_id}"
                            html_parts.append(f'<tr><td><iframe width="560" height="315" src="{embed_url}" frameborder="0" allowfullscreen></iframe></td></tr>')

                final_html = "\n".join(html_parts)
                content = content.replace("@MESSAGE@", final_html)

                with open(modified_file_path, "w") as file:
                    file.write(content)
            except json.JSONDecodeError:
                print("Invalid JSON format provided for --temp-json")
                exit(1)

        file_path = modified_file_path
    else:
        file_path = os.path.abspath(args.file) if args.file else None

    win = HtmlViewer(
        file_path,
        args.show_close_button,
        args.full_screen,
        args.url,
        args.text,
        args.text_size,
        args.titlebar,
        timeout=args.timeout
    )
    Gtk.main()

if __name__ == "__main__":
    main()
