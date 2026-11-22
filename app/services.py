"""Hardcoded service catalog, including durations and prices in tenge."""

CATALOGS = {
    "beauty": [
        {
            "id": "manicure",
            "name": "Маникюр",
            "services": [
                {"id": "manicure-basic", "name": "Обработка", "duration_minutes": 45, "price_kzt": 5000},
                {"id": "manicure-gel", "name": "Маникюр без укрепления", "duration_minutes": 90, "price_kzt": 6000},
                {"id": "manicure-strengthening", "name": "Маникюр с укреплением", "duration_minutes": 120, "price_kzt": 7000},
                {"id": "manicure-extension", "name": "Наращивание ногтей", "duration_minutes": 150, "price_kzt": 8000},
                {"id": "manicure-french", "name": "Френч", "duration_minutes": 30, "price_kzt": 1000},
            ],
        },
        {
            "id": "pedicure",
            "name": "Педикюр",
            "services": [
                {"id": "pedicure-basic", "name": "Педикюр (обработка)", "duration_minutes": 40, "price_kzt": 5000},
                {"id": "pedicure-gel", "name": "Педикюр с покрытием", "duration_minutes": 60, "price_kzt": 7000},
                {"id": "pedicure-heels", "name": "Обработка пяточек", "duration_minutes": 30, "price_kzt": 4000},
            ],
        },
        {
            "id": "sugaring",
            "name": "Шугаринг",
            "services": [
                {
                    "id": "sugaring-classic-set",
                    "name": "Комплекс «Классика»",
                    "description": "Подмышки + глубокое бикини + ноги до колен",
                    "duration_minutes": 40,
                    "price_kzt": 8000,
                },
                {
                    "id": "sugaring-all-inclusive",
                    "name": "Комплекс «Всё включено»",
                    "description": "Подмышки + руки полностью + глубокое бикини + ноги полностью",
                    "duration_minutes": 90,
                    "price_kzt": 12000,
                },
                {"id": "sugaring-face", "name": "Лицо полностью", "duration_minutes": 30, "price_kzt": 3000},
                {"id": "sugaring-upper-lip", "name": "Усики", "duration_minutes": 10, "price_kzt": 1000},
                {"id": "sugaring-sideburns", "name": "Баки", "duration_minutes": 10, "price_kzt": 1000},
                {"id": "sugaring-underarms", "name": "Подмышечная зона", "duration_minutes": 10, "price_kzt": 1500},
                {"id": "sugaring-arms-half", "name": "Руки до локтя", "duration_minutes": 30, "price_kzt": 3000},
                {"id": "sugaring-arms-full", "name": "Руки полностью", "duration_minutes": 40, "price_kzt": 4000},
                {"id": "sugaring-bikini", "name": "Бикини классика", "duration_minutes": 15, "price_kzt": 4000},
                {"id": "sugaring-deep-bikini", "name": "Бикини глубокое", "duration_minutes": 30, "price_kzt": 5000},
                {"id": "sugaring-belly", "name": "Живот", "duration_minutes": 20, "price_kzt": 3000},
                {"id": "sugaring-lower-back", "name": "Поясница", "duration_minutes": 20, "price_kzt": 3000},
                {"id": "sugaring-legs-full", "name": "Ноги полностью", "duration_minutes": 40, "price_kzt": 5000},
                {"id": "sugaring-legs-half", "name": "Ноги до колен", "duration_minutes": 30, "price_kzt": 4000},
            ],
        },
    ],
}


def categories_for(master):
    return CATALOGS.get(master.get("catalog", ""), [])


def find_service(master, service_id):
    for category in categories_for(master):
        for service in category["services"]:
            if service["id"] == service_id:
                return {**service, "category": category["name"]}
    return None


def format_price(price_kzt):
    return f"{price_kzt:,}".replace(",", " ") + " ₸"
