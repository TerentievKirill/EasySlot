"""Small, code-defined service catalogs for masters with variable appointments.

Prices are intentionally absent: the business owner has not provided them yet.
Change names and estimated durations here before inviting customers.
"""

CATALOGS = {
    "beauty": [
        {
            "id": "manicure",
            "name": "Маникюр",
            "services": [
                {"id": "manicure-basic", "name": "Маникюр без покрытия", "duration_minutes": 60},
                {"id": "manicure-gel", "name": "Маникюр с гель-лаком", "duration_minutes": 120},
                {"id": "manicure-removal-gel", "name": "Снятие, маникюр и покрытие", "duration_minutes": 150},
                {"id": "manicure-strengthening", "name": "Маникюр с укреплением", "duration_minutes": 150},
            ],
        },
        {
            "id": "pedicure",
            "name": "Педикюр",
            "services": [
                {"id": "pedicure-basic", "name": "Педикюр без покрытия", "duration_minutes": 60},
                {"id": "pedicure-gel", "name": "Педикюр с гель-лаком", "duration_minutes": 120},
                {"id": "pedicure-toes", "name": "Обработка пальчиков", "duration_minutes": 45},
                {"id": "pedicure-toes-gel", "name": "Обработка пальчиков с покрытием", "duration_minutes": 90},
            ],
        },
        {
            "id": "sugaring",
            "name": "Шугаринг",
            "services": [
                {"id": "sugaring-underarms", "name": "Подмышки", "duration_minutes": 30},
                {"id": "sugaring-legs-half", "name": "Голени", "duration_minutes": 45},
                {"id": "sugaring-legs-full", "name": "Ноги полностью", "duration_minutes": 60},
                {"id": "sugaring-bikini", "name": "Классическое бикини", "duration_minutes": 45},
                {"id": "sugaring-deep-bikini", "name": "Глубокое бикини", "duration_minutes": 60},
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
