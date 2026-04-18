from utils.schema import CamelCaseModel


class EnumOptionResponse(CamelCaseModel):
    value: str
    label: str


class EnumsResponse(CamelCaseModel):
    asset_type: list[EnumOptionResponse]
    event_type: list[EnumOptionResponse]
    event_status: list[EnumOptionResponse]
    event_access_type: list[EnumOptionResponse]
    ticket_category: list[EnumOptionResponse]
    location_mode: list[EnumOptionResponse]
    scan_status: list[EnumOptionResponse]
