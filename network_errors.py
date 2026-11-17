"""Safe network diagnostics without response bodies, URLs or credentials."""
import socket
import ssl
import urllib.error


def explain(error):
    reason=error.reason if isinstance(error,urllib.error.URLError) else error
    if isinstance(reason,ssl.SSLCertVerificationError):
        return ('TLS_CERTIFICATE: Python не смог проверить сертификат сервера. Проверьте дату и время Windows. '
                'Если используется антивирусная HTTPS-проверка или корпоративный прокси, нужен его доверенный сертификат в Windows/Python. Проверка сертификатов не отключена.')
    if isinstance(reason,ssl.SSLError):
        return 'TLS_HANDSHAKE: не удалось установить защищённое соединение. Возможна несовместимость сервера, VPN или HTTPS-проверки антивируса.'
    if isinstance(reason,socket.gaierror):
        return 'DNS: не удалось определить адрес сервера. Проверьте домен в базовом URL и доступность сайта; VPN только в браузере не обеспечивает доступ для Python.'
    if isinstance(reason,(TimeoutError,socket.timeout)):
        return 'TIMEOUT: сервер или сетевой посредник не ответил за отведённое время. Проверьте доступ к сайту и работает ли VPN для всего компьютера, а не только браузера.'
    if isinstance(reason,ConnectionRefusedError) or getattr(reason,'winerror',None)==10061:
        return 'CONNECTION_REFUSED: соединение отклонено сервером или прокси. Проверьте, запущен ли ваш прокси/VPN и верны ли его настройки.'
    if isinstance(reason,ConnectionResetError) or getattr(reason,'winerror',None)==10054:
        return 'CONNECTION_RESET: соединение прервано сервером или сетевым ПО. Проверьте VPN, прокси и правила брандмауэра для Python.'
    # Inspect only for classification; never echo raw exception text (may contain secrets).
    if 'tunnel connection failed' in str(reason).lower():
        return 'PROXY_TUNNEL: прокси не разрешил защищённое соединение с API. Проверьте системные настройки прокси/VPN; браузер и Python могут использовать разные маршруты.'
    return 'NETWORK: ошибка сетевого соединения Python. Проверьте базовый URL, системный прокси/VPN и доступ Python в брандмауэре. Причина пока не установлена.'
