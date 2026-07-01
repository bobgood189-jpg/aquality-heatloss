"""FSM states for the calculation wizard, registration, and shop flow (aiogram 3.x)."""
from aiogram.fsm.state import State, StatesGroup


class Purchase(StatesGroup):
    choosing_plan      = State()   # PRO / MAX
    choosing_duration  = State()   # 1 / 3 / 6 / 12 months
    asking_promo       = State()   # has promo?
    entering_promo     = State()   # type the promo code
    entering_email     = State()   # type the email
    confirming_order   = State()   # review order summary
    awaiting_screenshot = State()  # waiting for payment screenshot


class Register(StatesGroup):
    email = State()
    name  = State()
    phone = State()


class Wizard(StatesGroup):
    lang = State()
    # object-level params
    floors = State()
    height = State()
    attic = State()
    airtight = State()
    regime = State()
    lambda_mode = State()
    # materials
    mat = State()
    # rooms
    rooms_menu = State()
    room_type = State()
    room_len = State()
    room_wid = State()
    room_walls = State()
    win_count = State()
    win_size = State()
    win_dir = State()
    door_count = State()
    door_size = State()
    door_dir = State()
    door_beta = State()
    # lead capture
    lead_name = State()
    lead_phone = State()
