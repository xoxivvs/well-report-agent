"""
Состояние агента — то, что он «помнит» между шагами.
Версия 0.3: добавлены метрики времени.
"""

from typing import Optional, TypedDict


class AgentState(TypedDict):
    # Вход
    query: str

    # После разбора запроса
    well_id: Optional[int]
    period: Optional[str]
    report_type: Optional[str]

    # Данные из источников
    production: Optional[dict]
    telemetry: Optional[dict]
    geo: Optional[dict]

    # Черновик отчёта
    report_id: Optional[int]
    pdf_path: Optional[str]
    anomalies: Optional[list]
    recommendations: Optional[list]

    # Подтверждение
    confirmation_status: Optional[str]

    # Отправка
    recipient: Optional[str]
    sent: Optional[bool]

    # Управление
    error: Optional[str]
    step_count: int

    # 📊 Метрики времени (новое)
    time_parse: Optional[float]        # секунды на разбор запроса
    time_collect: Optional[float]      # секунды на сбор данных
    time_draft: Optional[float]        # секунды на генерацию PDF
    time_confirm: Optional[float]      # секунды на проверку подтверждения
    time_total: Optional[float]        # общее время
