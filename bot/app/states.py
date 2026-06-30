"""FSM states for the calculation wizard and user registration (aiogram 3.x)."""
from aiogram.fsm.state import State, StatesGroup


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
