from aiogram.fsm.state import State, StatesGroup


class EmployerOnboarding(StatesGroup):
    company_name = State()


class JobRequestCreation(StatesGroup):
    category = State()
    title = State()
    description = State()
    metro = State()
    hourly_rate = State()
    workers_needed = State()
    shift_dates = State()
    shift_start_time = State()
    shift_end_time = State()
    optional_menu = State()
    optional_address = State()
    optional_experience = State()
    optional_gender = State()
    optional_min_age = State()
    optional_max_age = State()
    optional_dress_code = State()
    optional_contact = State()
    optional_lunch = State()
    post_to_groups = State()
    confirm = State()
