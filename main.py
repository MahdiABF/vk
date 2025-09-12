# =========================
# 📦 Import libraries
# =========================
import platform

from kivy.utils import platform as core_platform
if core_platform == "android":
    from plyer import share


from kivymd.uix.button import MDRaisedButton       # برای دکمه‌ها
from kivymd.uix.dialog import MDDialog             # برای انتخاب طعم
from kivymd.uix.list import OneLineListItem        # برای لیست طعم‌ها
from reportlab.pdfgen import canvas                # برای ساخت PDF
from datetime import datetime                      # برای تاریخ فاکتور

from kivy.lang import Builder
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image   # 👈 جایگزین FitImage
from kivy.properties import StringProperty
from kivy.metrics import dp
from kivy.factory import Factory

from kivymd.app import MDApp
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.tab import MDTabs, MDTabsBase
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.filemanager import MDFileManager
from kivymd.uix.list import (
    MDList,
    TwoLineAvatarIconListItem,
    ImageLeftWidget,
    IconRightWidget,
    OneLineListItem,
)
from kivymd.toast import toast

import os
import uuid
import json


# =========================
# ⚙️ Config
# =========================
if platform.system() != "Android":
    Window.size = (420, 720)
DATA_FILE = "data.json"


# =========================
# 🏷️ Tab class
# =========================
class Tab(MDFloatLayout, MDTabsBase):
    pass

# =========================
# 🎨 KV String (UI Layouts)
# =========================
KV = '''
#:import dp kivy.metrics.dp

MDScreen:
    MDTabs:
        id: tabs
        tab_indicator_height: 4
        tab_indicator_color: app.theme_cls.primary_color


<AddEditProductContent@BoxLayout>:
    orientation: "vertical"
    spacing: dp(10)
    size_hint_y: None
    padding: dp(8)
    height: self.minimum_height

    MDTextField:
        id: name_field
        hint_text: "Product name"
        helper_text_mode: "on_error"

    MDTextField:
        id: pack_count_field
        hint_text: "Units per pack"
        input_filter: "int"
        helper_text_mode: "on_error"

    MDTextField:
        id: consumer_price_field
        hint_text: "MSRP"
        helper_text_mode: "on_error"

    MDTextField:
        id: unit_price_field
        hint_text: "Unit price"
        helper_text_mode: "on_error"

    MDTextField:
        id: carton_price_field
        hint_text: "Carton price"
        helper_text_mode: "on_error"

    # ✅ اضافه کردن فیلد طعم‌ها
    MDTextField:
        id: flavors_field
        hint_text: "Flavors (comma separated)"
        helper_text_mode: "on_error"

    BoxLayout:
        size_hint_y: None
        height: dp(40)
        spacing: dp(8)
        MDRaisedButton:
            text: "Choose image"
            on_release: app.open_file_manager()
        MDFlatButton:
            id: image_label
            text: "No image selected"
            on_release: app.open_file_manager()

'''

# =========================
# 🚀 Main App
# =========================
class VisitorApp(MDApp):
    selected_image_path = StringProperty("")

    # ---------- 🔨 Build ----------
    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.root = Builder.load_string(KV)

        # datasets
        self.products = {}
        self.product_widgets = {}
        self.cart = {}

        # Load saved data
        self.load_data()

        # Tabs
        tabs = self.root.ids.tabs
        for title in ["Customer", "Products", "Cart", "Visitor"]:  # ⬅ تب جدید
            tab = Tab(title=title)
            if title == "Products":
                tab.add_widget(self.build_product_tab())
                for pid in self.products.keys():
                    self._add_product_widget(pid)
            elif title == "Cart":
                tab.add_widget(self.build_cart_tab())
                self._refresh_cart_tab()
            elif title == "Visitor":  # ⬅ ساختن تب ویترین
                tab.add_widget(self.build_visitor_tab())
                self._refresh_visitor_tab()
            else:
                from kivymd.uix.label import MDLabel
                box = BoxLayout(orientation="vertical", padding=dp(16))
                box.add_widget(MDLabel(text="Customer section", halign="center"))
                tab.add_widget(box)
            tabs.add_widget(tab)
        return self.root

    # =========================
    # 👀 Visitor Tab
    # =========================
    def build_visitor_tab(self):
        root = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        self.visitor_list = MDList()
        scroll = ScrollView()
        scroll.add_widget(self.visitor_list)
        root.add_widget(scroll)
        return root

    def _refresh_visitor_tab(self):
        if not hasattr(self, "visitor_list"):
            return
        self.visitor_list.clear_widgets()
        from kivymd.uix.card import MDCard
        from kivymd.uix.label import MDLabel

        for pid, p in self.products.items():
            card = MDCard(
                orientation="vertical",
                size_hint=(1, None),
                height=dp(300),
                padding=dp(8),
                spacing=dp(8),
                radius=[12, 12, 12, 12],
                style="elevated",
            )
            # تصویر محصول
            img_src = p["image_path"] if p.get("image_path") and os.path.exists(p["image_path"]) else ""
            image = Image(
                source=img_src,
                allow_stretch=True,
                keep_ratio=True,
                size_hint_y=None,
                height=dp(160)
            )
            # image.size_hint_y = 1.6
            card.add_widget(image)

            # متن‌ها زیر عکس
            box = BoxLayout(orientation="vertical", spacing=4, padding=dp(4))
            box.add_widget(MDLabel(text=p["name"], halign="center", theme_text_color="Primary"))
            box.add_widget(MDLabel(text=f"Unit: {self._fmt_num(p['unit_price'])}", halign="center"))
            box.add_widget(MDLabel(text=f"Carton: {self._fmt_num(p['carton_price'])}", halign="center"))
            box.add_widget(MDLabel(text=f"Pack: {p['pack_count']}", halign="center"))
            if p.get("flavors"):
                box.add_widget(MDLabel(text=f"Flavors: {', '.join(p['flavors'])}", halign="center"))
            card.add_widget(box)

            # 👇 دکمه افزودن به سبد
            btn_add = MDRaisedButton(
                text="Add to cart",
                pos_hint={"center_x": 0.5},
                on_release=lambda _, pid=pid: self._handle_add_to_cart(pid)
            )
            card.add_widget(btn_add)

            self.visitor_list.add_widget(card)

    def _handle_add_to_cart(self, product_id):
        product = self.products[product_id]
        flavors = product.get("flavors", [])
        if flavors:
            from kivymd.uix.list import MDList, OneLineListItem
            content = MDList()
            for flavor in flavors:
                item = OneLineListItem(
                    text=flavor,
                    on_release=lambda x, f=flavor: self._confirm_add_flavor(product_id, f)
                )
                content.add_widget(item)

            self.flavor_dialog = MDDialog(
                title="Choose flavor",
                type="custom",
                content_cls=content,
                size_hint=(0.8, None)
            )
            self.flavor_dialog.open()
        else:
            self.add_to_cart(product_id)

    def _confirm_add_flavor(self, product_id, flavor):
        """افزودن محصول با طعم انتخاب‌شده"""
        self.add_to_cart(product_id, flavor=flavor)
        self.flavor_dialog.dismiss()

    # =========================
    # 💾 Data Management
    # =========================
    def save_data(self):
        """ذخیره محصولات و سبد در فایل JSON"""
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    {"products": self.products, "cart": self.cart},
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except Exception as e:
            print("Error saving data:", e)

    def load_data(self):
        """بارگذاری محصولات و سبد از فایل JSON"""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.products = data.get("products", {})
                    self.cart = data.get("cart", {})
            except Exception as e:
                print("Error loading data:", e)

    # =========================
    # 📦 Products Tab
    # =========================
    def build_product_tab(self):
        root = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        buttons_row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        buttons_row.add_widget(MDRaisedButton(
            text="Add product",
            on_release=lambda *_: self.open_add_edit_dialog()
        ))
        root.add_widget(buttons_row)
        self.product_list = MDList()
        scroll = ScrollView()
        scroll.add_widget(self.product_list)
        root.add_widget(scroll)
        return root

    def open_add_edit_dialog(self, product_id=None):
        self.selected_image_path = ""
        self._dialog_mode_edit = product_id is not None
        content = Factory.AddEditProductContent()
        title = "Edit product" if self._dialog_mode_edit else "Add product"
        if self._dialog_mode_edit:
            p = self.products[product_id]
            content.ids.name_field.text = p["name_raw"]
            content.ids.flavors_field.text = ", ".join(p.get("flavors", []))
            content.ids.pack_count_field.text = str(p["pack_count"])
            content.ids.consumer_price_field.text = self._fmt_num(p["consumer_price"])
            content.ids.unit_price_field.text = self._fmt_num(p["unit_price"])
            content.ids.carton_price_field.text = self._fmt_num(p["carton_price"])
            if p.get("image_path"):
                content.ids.image_label.text = os.path.basename(p["image_path"])
                self.selected_image_path = p["image_path"]
        self.product_dialog = MDDialog(
            title=title,
            type="custom",
            auto_dismiss=False,
            content_cls=content,
            buttons=[
                MDFlatButton(text="Cancel", on_release=lambda *_: self.product_dialog.dismiss()),
                MDRaisedButton(text="Save", on_release=lambda *_: self.save_product(product_id))
            ],
        )
        self.product_dialog.open()

    def open_file_manager(self):
        start_path = os.path.expanduser("~")
        self.file_manager = MDFileManager(
            select_path=self._select_image_path,
            exit_manager=self._close_file_manager,
            ext=['.png', '.jpg', '.jpeg', '.webp', '.bmp']
        )
        self.file_manager.show(start_path)

    def _close_file_manager(self, *args):
        try:
            self.file_manager.close()
        except Exception:
            pass

    def _select_image_path(self, path):
        self.selected_image_path = path
        if hasattr(self, "product_dialog") and self.product_dialog and self.product_dialog.content_cls:
            self.product_dialog.content_cls.ids.image_label.text = os.path.basename(path)
        self._close_file_manager()

    def _parse_float(self, s, default=0.0):
        try:
            return float(str(s).replace(",", "").strip())
        except Exception:
            return default

    def _fmt_num(self, x):
        try:
            return f"{float(x):.2f}".rstrip("0").rstrip(".")
        except Exception:
            return str(x)

    def save_product(self, product_id=None):
        c = self.product_dialog.content_cls
        name = (c.ids.name_field.text or "").strip()
        pack_count = (c.ids.pack_count_field.text or "").strip()
        consumer_price = (c.ids.consumer_price_field.text or "").strip()
        unit_price = (c.ids.unit_price_field.text or "").strip()
        carton_price = (c.ids.carton_price_field.text or "").strip()
        if not name:
            toast("Enter product name")
            return
        pack_count = int(pack_count) if pack_count.isdigit() else 0
        consumer_price = self._parse_float(consumer_price)
        unit_price = self._parse_float(unit_price)
        carton_price = self._parse_float(carton_price)
        image_path = self.selected_image_path or (self.products.get(product_id, {}).get("image_path") if product_id else "")

        # خواندن طعم‌ها
        flavors_text = (c.ids.flavors_field.text or "").strip()
        flavors_list = [f.strip() for f in flavors_text.split(",") if f.strip()]
        data = {
            "name_raw": name,
            "name": name,
            "pack_count": pack_count,
            "consumer_price": consumer_price,
            "unit_price": unit_price,
            "carton_price": carton_price,
            "image_path": image_path,
            "flavors": flavors_list  # ذخیره طعم‌ها
        }
        if product_id is None:
            product_id = str(uuid.uuid4())
            self.products[product_id] = data
            self._add_product_widget(product_id)
            toast("Product added")
        else:
            self.products[product_id].update(data)
            self._refresh_product_widget(product_id)
            toast("Product updated")
        self.product_dialog.dismiss()
        self._refresh_cart_tab()
        self.save_data()

    def _make_secondary_text(self, product_id):
        p = self.products[product_id]
        parts = [
            f"Unit: {self._fmt_num(p['unit_price'])}",
            f"Carton: {self._fmt_num(p['carton_price'])}",
            f"Pack: {p['pack_count']}",
        ]
        if p.get("flavors"):
            parts.append(f"Flavors: {', '.join(p['flavors'])}")
        qty = self.cart.get(product_id, 0)
        if qty > 0:
            parts.append(f"In cart: {qty}")
        return " | ".join(parts)

    def _add_product_widget(self, product_id):
        p = self.products[product_id]
        from kivymd.uix.card import MDCard
        from kivymd.uix.label import MDLabel
        from kivy.uix.boxlayout import BoxLayout
        from kivymd.uix.button import MDIconButton
        from kivy.uix.widget import Widget

        card = MDCard(
            orientation="vertical",
            size_hint=(1, None),
            height=dp(170),  # ارتفاع کمی بزرگ‌تر
            padding=dp(8),
            spacing=dp(4),
            radius=[12, 12, 12, 12],
            style="elevated",
        )

        # Spacer برای فاصله از بالا
        card.add_widget(Widget(size_hint_y=None, height=dp(8)))  # فاصله ۸dp از بالا

        # تصویر محصول
        img_src = p.get("image_path", "")
        if not img_src or not os.path.isfile(img_src):
            img_src = os.path.join("assets", "placeholder.png")

        image = Image(source=img_src, size_hint_y=None, height=dp(80), allow_stretch=True)
        card.add_widget(image)

        # متن‌ها
        box_text = BoxLayout(orientation="vertical", size_hint_y=None)
        box_text.bind(minimum_height=box_text.setter('height'))

        name_label = MDLabel(
            text=p["name"],
            halign="center",
            size_hint_y=None,
            height=dp(20),
            shorten=True,
            shorten_from='right',
        )
        box_text.add_widget(name_label)

        secondary_text = self._make_secondary_text(product_id)
        secondary_label = MDLabel(
            text=secondary_text,
            halign="center",
            size_hint_y=None,
            height=dp(20),
            text_size=(dp(380), None),
            shorten=True,
            shorten_from='right',
        )
        box_text.add_widget(secondary_label)

        card.add_widget(box_text)

        # دکمه‌ها در یک BoxLayout افقی
        btn_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(4))
        btn_minus = MDIconButton(icon="minus-circle", on_release=lambda *_: self.decrease_from_cart(product_id))
        btn_edit = MDIconButton(icon="pencil", on_release=lambda *_: self.open_add_edit_dialog(product_id))
        btn_delete = MDIconButton(icon="delete", on_release=lambda *_: self.delete_product(product_id))
        btn_row.add_widget(btn_minus)
        btn_row.add_widget(btn_edit)
        btn_row.add_widget(btn_delete)

        card.add_widget(btn_row)

        self.product_widgets[product_id] = card
        self.product_list.add_widget(card)

    def _refresh_product_widget(self, product_id):
        if product_id not in self.product_widgets:
            return
        item = self.product_widgets[product_id]
        self.product_list.remove_widget(item)
        self._add_product_widget(product_id)

    def delete_product(self, product_id):
        self.products.pop(product_id, None)
        if product_id in self.product_widgets:
            self.product_list.remove_widget(self.product_widgets[product_id])
            self.product_widgets.pop(product_id, None)
        if product_id in self.cart:
            self.cart.pop(product_id, None)
            self._refresh_cart_tab()
        toast("Product deleted")
        self.save_data()

    # ---------- Cart ----------
    def add_to_cart(self, product_id, amount=1, flavor=None):
        """افزودن محصول به سبد با امکان طعم"""
        key = f"{product_id}_{flavor}" if flavor else product_id
        self.cart[key] = self.cart.get(key, 0) + amount
        self._refresh_product_widget(product_id)
        self._refresh_cart_tab()
        self.save_data()

    def decrease_from_cart(self, product_id, amount=1, flavor=None):
        key = f"{product_id}_{flavor}" if flavor else product_id
        if key in self.cart:
            self.cart[key] -= amount
            if self.cart[key] <= 0:
                self.cart.pop(key, None)
        self._refresh_product_widget(product_id)
        self._refresh_cart_tab()
        self.save_data()

    def remove_from_cart(self, product_id, flavor=None):
        key = f"{product_id}_{flavor}" if flavor else product_id
        if key in self.cart:
            self.cart.pop(key)
        self._refresh_product_widget(product_id)
        self._refresh_cart_tab()
        self.save_data()

    def add_to_cart_key(self, key, amount=1):
        self.cart[key] = self.cart.get(key, 0) + amount
        self._refresh_cart_tab()
        self.save_data()

    def decrease_from_cart_key(self, key, amount=1):
        if key in self.cart:
            self.cart[key] -= amount
            if self.cart[key] <= 0:
                self.cart.pop(key)
        self._refresh_cart_tab()
        self.save_data()

    def remove_from_cart_key(self, key):
        if key in self.cart:
            self.cart.pop(key)
        self._refresh_cart_tab()
        self.save_data()

    # =========================
    # 🛒 Cart Tab
    # =========================
    def build_cart_tab(self):
        root = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        buttons_row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        buttons_row.add_widget(MDRaisedButton(
            text="Generate PDF",
            on_release=lambda *_: self.generate_pdf_invoice()
        ))

        root.add_widget(buttons_row)
        self.cart_list = MDList()
        scroll = ScrollView()
        scroll.add_widget(self.cart_list)
        root.add_widget(scroll)
        return root

    def _refresh_cart_tab(self):
        if not hasattr(self, "cart_list"):
            return
        self.cart_list.clear_widgets()
        total = 0.0

        for key, qty in self.cart.items():
            if "_" in key:
                product_id, flavor = key.split("_")
            else:
                product_id = key
                flavor = None

            if product_id not in self.products:
                continue

            p = self.products[product_id]
            line_total = p["unit_price"] * qty
            total += line_total

            from kivymd.uix.card import MDCard
            from kivymd.uix.label import MDLabel
            from kivy.uix.boxlayout import BoxLayout
            from kivymd.uix.button import MDRaisedButton

            card = MDCard(
                orientation="vertical",
                size_hint_y=None,
                height=dp(150),
                padding=dp(8),
                spacing=dp(4),
                radius=[12, 12, 12, 12],
                style="elevated"
            )

            # ✅ اضافه کردن تصویر
            img_src = p.get("image_path", "")
            if not img_src or not os.path.exists(img_src):
                img_src = "placeholder.png"  # تصویر پیش‌فرض
            image = Image(
                source=img_src,
                size_hint=(1, None),
                height=dp(80),
                allow_stretch=True,
                keep_ratio=True
            )
            card.add_widget(image)

            name_text = p["name"]
            if flavor:
                name_text += f" ({flavor})"

            card.add_widget(MDLabel(
                text=f"{name_text} - Qty: {qty} - Unit: {self._fmt_num(p['unit_price'])} - Total: {self._fmt_num(line_total)}",
                halign="center"
            ))

            # دکمه‌ها
            btn_row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(4))
            btn_row.add_widget(MDRaisedButton(text="-", on_release=lambda _, k=key: self.decrease_from_cart_key(k)))
            btn_row.add_widget(MDRaisedButton(text="+", on_release=lambda _, k=key: self.add_to_cart_key(k)))
            btn_row.add_widget(MDRaisedButton(text="Delete", on_release=lambda _, k=key: self.remove_from_cart_key(k)))
            card.add_widget(btn_row)

            self.cart_list.add_widget(card)

        total_item = OneLineListItem(text=f"Grand total: {self._fmt_num(total)}")
        self.cart_list.add_widget(total_item)

    def remove_from_cart(self, product_id):
        if product_id in self.cart:
            self.cart.pop(product_id)
        self._refresh_product_widget(product_id)
        self._refresh_cart_tab()
        self.save_data()

    def clear_cart(self):
        self.cart.clear()
        self._refresh_cart_tab()
        for pid in list(self.product_widgets.keys()):
            self._refresh_product_widget(pid)
        self.save_data()

    # =========================
    # generate_pdf_invoice
    # =========================
    def generate_pdf_invoice(self):
        if not self.cart:
            toast("Cart is empty")
            return

        filename = f"Invoice_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        c = canvas.Canvas(filename)
        c.setFont("Helvetica", 12)
        y = 800
        c.drawString(50, y, "Invoice")
        y -= 30
        total_amount = 0.0

        for key, qty in self.cart.items():
            if "_" in str(key):
                product_id, flavor = key.split("_")
            else:
                product_id = key
                flavor = None
            product = self.products.get(product_id, {})
            name = product.get("name", "Unknown")
            if flavor:
                name += f" ({flavor})"
            unit_price = product.get("unit_price", 0)
            line_total = unit_price * qty
            total_amount += line_total
            c.drawString(50, y, f"{name} - Qty: {qty} - Unit: {unit_price} - Total: {line_total}")
            y -= 20

        c.drawString(50, y - 20, f"Grand Total: {total_amount}")
        c.save()
        toast(f"Invoice saved as {filename}")

        if platform.system() == "Android":
            try:
                share.share(filepath=filename)
            except Exception as e:
                toast(f"Cannot share PDF: {e}")


# =========================
# ▶️ Run App
# =========================
if __name__ == "__main__":
    VisitorApp().run()
