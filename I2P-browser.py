import os
import sys
import socket
from urllib.parse import urlsplit, quote_plus

PROXY_HOST = "127.0.0.1"

HTTP_PROXY_PORT = 4444
HTTPS_PROXY_PORT = 4445

HOME_URL = "http://legwork.i2p/"
CONSOLE_URL = "http://127.0.0.1:7657/"

os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
    f"--proxy-server=http={PROXY_HOST}:{HTTP_PROXY_PORT};"
    f"https={PROXY_HOST}:{HTTPS_PROXY_PORT} "
    "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1 "
    "--disable-quic "
    "--disable-background-networking"
)

from PyQt5.QtCore import (
    Qt, QUrl, QByteArray, QObject, pyqtSignal, QTimer
)

from PyQt5.QtGui import QIcon, QKeySequence

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QToolBar,
    QLineEdit, QAction, QLabel, QCheckBox,
    QDockWidget, QListWidget, QStatusBar, QMenu
)

from PyQt5.QtWebEngineWidgets import (
    QWebEngineView, QWebEnginePage,
    QWebEngineProfile, QWebEngineSettings
)

from PyQt5.QtWebEngineCore import (
    QWebEngineUrlRequestInterceptor
)

class RequestLogger(QObject):
    request = pyqtSignal(str)


class RequestInterceptor(QWebEngineUrlRequestInterceptor):

    def __init__(self, logger):
        super().__init__()

        self.logger = logger
        self.enabled = True

        self.headers = [
            ("Accept", "text/html,application/xhtml+xml,"
             "application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"),

            ("Accept-Language", "en-GB,en;q=0.9"),
        ]

    def interceptRequest(self, info):

        if not self.enabled:
            return

        try:
            url = info.requestUrl().toString()

            method = bytes(
                info.requestMethod()
            ).decode("utf-8", errors="replace")

            resource = str(info.resourceType())

            self.logger.request.emit(
                f"{method} | {resource} | {url}"
            )

        except Exception as error:
            self.logger.request.emit(
                f"Interceptor error: {error}"
            )

        for name, value in self.headers:

            info.setHttpHeader(
                QByteArray(name.encode()),
                QByteArray(value.encode())
            )


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        print("[+] Initialising browser")

        self.setWindowTitle("I2P Browser")
        self.resize(1450, 950)

        self.logger = RequestLogger()

        self.profile = QWebEngineProfile(self)

        self.profile.setHttpCacheType(
            QWebEngineProfile.MemoryHttpCache
        )

        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.NoPersistentCookies
        )

        self.profile.setHttpUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

        self.cookie_filter = None

        self.set_cookie_filter(True)

        self.interceptor = RequestInterceptor(
            self.logger
        )

        self.profile.setUrlRequestInterceptor(
            self.interceptor
        )

        self.tabs = QTabWidget()

        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.setDocumentMode(True)

        self.tabs.tabCloseRequested.connect(
            self.close_tab
        )

        self.tabs.currentChanged.connect(
            self.update_address
        )

        self.setCentralWidget(self.tabs)

        toolbar = QToolBar("Navigation")

        toolbar.setMovable(False)

        self.addToolBar(toolbar)

        self.add_action(toolbar, "Back", self.go_back)
        self.add_action(toolbar, "Forward", self.go_forward)
        self.add_action(toolbar, "Reload", self.reload_page)
        self.add_action(toolbar, "Stop", self.stop_loading)
        self.add_action(toolbar, "Home", self.go_home)

        toolbar.addSeparator()

        self.add_action(
            toolbar, "New Tab",
            lambda: self.add_tab(HOME_URL)
        )

        self.add_action(
            toolbar, "Router Console",
            lambda: self.add_tab(CONSOLE_URL)
        )

        self.url_bar = QLineEdit()

        self.url_bar.setPlaceholderText(
            "Enter URL, hostname or search..."
        )

        self.url_bar.returnPressed.connect(
            self.navigate
        )

        toolbar.addWidget(self.url_bar)

        self.js_toggle = QCheckBox("JavaScript")
        self.js_toggle.setChecked(True)

        self.js_toggle.stateChanged.connect(
            self.toggle_javascript
        )

        toolbar.addWidget(self.js_toggle)

        self.cookie_toggle = QCheckBox(
            "Block third-party cookies"
        )

        self.cookie_toggle.setChecked(True)

        self.cookie_toggle.stateChanged.connect(
            self.toggle_cookies
        )

        toolbar.addWidget(self.cookie_toggle)

        self.log_toggle = QCheckBox("Logging")
        self.log_toggle.setChecked(True)

        self.log_toggle.stateChanged.connect(
            lambda state: setattr(
                self.interceptor,
                "enabled",
                state == Qt.Checked
            )
        )

        toolbar.addWidget(self.log_toggle)

        self.network_dock = QDockWidget(
            "Network Inspector", self
        )

        self.network_list = QListWidget()

        self.network_dock.setWidget(
            self.network_list
        )

        self.addDockWidget(
            Qt.BottomDockWidgetArea,
            self.network_dock
        )

        self.logger.request.connect(
            self.add_request
        )

        self.add_action(
            toolbar,
            "Clear Log",
            self.network_list.clear
        )

        view_menu = self.menuBar().addMenu("View")

        toggle_network = QAction(
            "Network Inspector", self
        )

        toggle_network.setCheckable(True)
        toggle_network.setChecked(True)

        toggle_network.triggered.connect(
            self.network_dock.setVisible
        )

        self.network_dock.visibilityChanged.connect(
            toggle_network.setChecked
        )

        view_menu.addAction(toggle_network)

        self.setStatusBar(QStatusBar())

        self.proxy_status = QLabel(
            "Proxy: checking..."
        )

        self.statusBar().addPermanentWidget(
            self.proxy_status
        )

        self.shortcut("Ctrl+T", lambda: self.add_tab(HOME_URL))
        self.shortcut("Ctrl+W", self.close_current_tab)
        self.shortcut("Ctrl+L", self.focus_address)
        self.shortcut("Ctrl+R", self.reload_page)
        self.shortcut("Ctrl+Tab", self.next_tab)
        self.shortcut("Ctrl+Shift+Tab", self.previous_tab)

        self.add_tab(HOME_URL)

        QTimer.singleShot(
            500, self.check_proxy
        )

        print("[+] Browser initialised")

    def add_action(self, toolbar, name, callback):

        action = QAction(name, self)
        action.triggered.connect(callback)

        toolbar.addAction(action)

        return action

    def shortcut(self, key, callback):

        action = QAction(self)
        action.setShortcut(QKeySequence(key))
        action.triggered.connect(callback)

        self.addAction(action)

    def current_browser(self):

        return self.tabs.currentWidget()

    def add_tab(self, url="about:blank"):

        print("[+] Creating tab:", url)

        browser = QWebEngineView()

        page = QWebEnginePage(
            self.profile,
            browser
        )

        browser.setPage(page)

        settings = page.settings()

        settings.setAttribute(
            QWebEngineSettings.JavascriptEnabled,
            self.js_toggle.isChecked()
        )

        settings.setAttribute(
            QWebEngineSettings.LocalStorageEnabled,
            False
        )

        settings.setAttribute(
            QWebEngineSettings.LocalContentCanAccessFileUrls,
            False
        )

        settings.setAttribute(
            QWebEngineSettings.LocalContentCanAccessRemoteUrls,
            False
        )

        settings.setAttribute(
            QWebEngineSettings.PluginsEnabled,
            False
        )

        index = self.tabs.addTab(
            browser, "New Tab"
        )

        self.tabs.setCurrentIndex(index)

        browser.urlChanged.connect(
            lambda url, b=browser:
            self.update_url(url, b)
        )

        browser.titleChanged.connect(
            lambda title, b=browser:
            self.update_title(title, b)
        )

        browser.loadStarted.connect(
            lambda b=browser:
            print("[+] Loading:", b.url().toString())
        )

        browser.loadFinished.connect(
            lambda success, b=browser:
            self.page_finished(success, b)
        )

        page.renderProcessTerminated.connect(
            lambda status, code:
            print(
                "[!] Chromium process terminated:",
                status, code
            )
        )

        browser.setUrl(QUrl(url))

        return browser

    def close_tab(self, index):

        if self.tabs.count() == 1:

            self.current_browser().setUrl(
                QUrl("about:blank")
            )

            self.tabs.setTabText(
                index, "New Tab"
            )

            return

        browser = self.tabs.widget(index)

        self.tabs.removeTab(index)

        browser.deleteLater()

    def close_current_tab(self):

        self.close_tab(
            self.tabs.currentIndex()
        )

    def next_tab(self):

        self.tabs.setCurrentIndex(
            (self.tabs.currentIndex() + 1)
            % self.tabs.count()
        )

    def previous_tab(self):

        self.tabs.setCurrentIndex(
            (self.tabs.currentIndex() - 1)
            % self.tabs.count()
        )

    def update_title(self, title, browser):

        index = self.tabs.indexOf(browser)

        if index != -1:

            self.tabs.setTabText(
                index,
                title[:25] if title else "New Tab"
            )

            self.tabs.setTabToolTip(
                index,
                browser.url().toString()
            )

    def navigate(self):

        address = self.url_bar.text().strip()

        if not address:
            return

        print("[+] Navigating:", address)

        if "://" not in address:

            if " " in address:

                address = (
                    "https://html.duckduckgo.com/html/?q="
                    + quote_plus(address)
                )

            elif address.endswith(".i2p"):

                address = "http://" + address

            elif address.startswith(
                ("localhost", "127.0.0.1")
            ):

                address = "http://" + address

            else:

                address = "https://" + address

        parsed = urlsplit(address)

        if parsed.scheme not in ("http", "https"):
            self.statusBar().showMessage(
                "Unsupported URL scheme"
            )
            return

        if not parsed.hostname:
            self.statusBar().showMessage(
                "Invalid hostname"
            )
            return

        self.current_browser().setUrl(
            QUrl(address)
        )

    def update_url(self, url, browser):

        if browser != self.current_browser():
            return

        address = url.toString()

        self.url_bar.setText(address)

        parsed = urlsplit(address)

        if parsed.scheme == "https" or (
            parsed.hostname and (
                parsed.hostname.endswith(".i2p")
                or parsed.hostname in (
                    "localhost", "127.0.0.1"
                )
            )
        ):

            self.url_bar.setStyleSheet(
                "color: green;"
            )

        else:

            self.url_bar.setStyleSheet(
                "color: red;"
            )

    def update_address(self, index):

        browser = self.tabs.widget(index)

        if browser:

            self.url_bar.setText(
                browser.url().toString()
            )

    def focus_address(self):

        self.url_bar.setFocus()
        self.url_bar.selectAll()

    def go_back(self):

        self.current_browser().back()

    def go_forward(self):

        self.current_browser().forward()

    def reload_page(self):

        self.current_browser().reload()

    def stop_loading(self):

        self.current_browser().stop()

    def go_home(self):

        self.current_browser().setUrl(
            QUrl(HOME_URL)
        )

    def toggle_javascript(self, state):

        enabled = state == Qt.Checked

        for i in range(self.tabs.count()):

            browser = self.tabs.widget(i)

            browser.settings().setAttribute(
                QWebEngineSettings.JavascriptEnabled,
                enabled
            )

    def set_cookie_filter(self, enabled):

        if enabled:

            self.cookie_filter = (
                lambda request: not request.thirdParty
            )

        else:

            self.cookie_filter = (
                lambda request: True
            )

        self.profile.cookieStore().setCookieFilter(
            self.cookie_filter
        )

    def toggle_cookies(self, state):

        self.set_cookie_filter(
            state == Qt.Checked
        )

    def add_request(self, request):

        self.network_list.addItem(request)

        while self.network_list.count() > 3000:

            self.network_list.takeItem(0)

        self.network_list.scrollToBottom()

    def check_proxy(self):
    
        results = []
    
        for name, port in [
            ("HTTP", HTTP_PROXY_PORT),
            ("HTTPS", HTTPS_PROXY_PORT)
        ]:
    
            try:
                with socket.create_connection(
                    (PROXY_HOST, port),
                    timeout=3
                ):
                    results.append(f"{name}: ONLINE")
                    print(f"[+] {name} proxy available on port {port}")

            except OSError as error:
                results.append(f"{name}: OFFLINE")
                print(f"[!] {name} proxy unavailable on port {port}: {error}")

        online = all("ONLINE" in result for result in results)

        self.proxy_status.setText(
            "Proxies: " + " | ".join(results)
        )

        self.proxy_status.setStyleSheet(
            "color: green;" if online else "color: red;"
        )

    def page_finished(self, success, browser):

        if success:

            print(
                "[+] Loaded:",
                browser.url().toString()
            )

            self.statusBar().showMessage(
                "Page loaded", 3000
            )

        else:

            print(
                "[!] Failed:",
                browser.url().toString()
            )

            self.statusBar().showMessage(
                "Page failed to load", 5000
            )

    def closeEvent(self, event):

        print("[+] Clearing browser data")

        self.profile.cookieStore().deleteAllCookies()
        self.profile.clearHttpCache()
        self.profile.clearAllVisitedLinks()

        event.accept()

if __name__ == "__main__":

    print("[+] Starting I2P Browser")

    app = QApplication(sys.argv)

    app.setApplicationName("I2P Browser")

    app.setWindowIcon(
        QIcon("i2p_icon.png")
    )

    window = MainWindow()

    window.showMaximized()

    print("[+] Application running")

    sys.exit(app.exec_())
