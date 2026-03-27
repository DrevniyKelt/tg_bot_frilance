from app.bot.keyboards import main_menu_keyboard
from app.bot.messages import help_text, profile_text, start_text
from app.schemas.profile import PublicUserProfile


def test_bot_main_keyboard_contains_navigation():
    keyboard = main_menu_keyboard()
    buttons = [button.text for row in keyboard.inline_keyboard for button in row]

    assert "Открыть Mini App" in buttons
    assert "Каталог заказов" in buttons
    assert "Swipe" in buttons
    assert "Профиль" in buttons
    assert "Мои заказы" in buttons


def test_bot_message_builders_render_profile_summary():
    profile = PublicUserProfile(
        id=1,
        display_name="Mihai Demo",
        role="both",
        headline="Full-stack",
        bio="Bio",
        locale="ru",
        wallet_balance="1200.00",
        avg_executor_rating="4.90",
        avg_client_rating="4.80",
        completed_deals=2,
        total_matches=3,
        active_tariff="Pro",
        stack=[],
    )

    assert "SkillLane" in start_text()
    assert "/profile" in help_text()
    summary = profile_text(profile)
    assert "Mihai Demo" in summary
    assert "Тариф: Pro" in summary
    assert "Completed: 2" in summary
