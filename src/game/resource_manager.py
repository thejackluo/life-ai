"""
Resource Management (MVP - Simplified)

Basic resource tracking and management. Can be expanded in future versions.
"""

from typing import Tuple, Optional

from src.core.models import Resources, GameState


def can_perform_action(
    resources: Resources,
    money_cost: float = 0.0,
    energy_cost: int = 0,
    time_cost_minutes: int = 0
) -> Tuple[bool, Optional[str]]:
    """
    Check if player has enough resources for an action.
    
    Args:
        resources: Player's resources
        money_cost: Money required
        energy_cost: Energy required
        time_cost_minutes: Time required in minutes
        
    Returns:
        Tuple of (can_perform, reason_if_cannot)
    """
    if money_cost > resources.money:
        return False, f"Not enough money (need ${money_cost:.2f}, have ${resources.money:.2f})"
    
    if energy_cost > resources.energy:
        return False, f"Not enough energy (need {energy_cost}, have {resources.energy})"
    
    # Check time availability (simplified: just check if it would push past midnight)
    hours_needed = time_cost_minutes / 60
    if resources.current_hour + hours_needed >= 24:
        return False, "Not enough time left today"
    
    return True, None


def perform_action(
    resources: Resources,
    money_cost: float = 0.0,
    energy_cost: int = 0,
    time_cost_minutes: int = 0
) -> bool:
    """
    Spend resources to perform an action.
    
    Args:
        resources: Player's resources
        money_cost: Money to spend
        energy_cost: Energy to spend
        time_cost_minutes: Time to spend
        
    Returns:
        True if action was performed
    """
    can_do, reason = can_perform_action(resources, money_cost, energy_cost, time_cost_minutes)
    
    if not can_do:
        print(f"  ⚠️  {reason}")
        return False
    
    resources.spend(money=money_cost, energy=energy_cost, time_minutes=time_cost_minutes)
    return True


def rest(resources: Resources, hours: int = 8) -> None:
    """
    Rest to restore energy.
    
    Args:
        resources: Player's resources
        hours: Hours to rest
    """
    # Restore energy
    energy_restored = min(100 - resources.energy, hours * 10)  # 10 energy per hour
    resources.restore_energy(energy_restored)
    
    # Advance time
    resources.current_hour += hours
    if resources.current_hour >= 24:
        resources.current_day += 1
        resources.current_hour = resources.current_hour % 24
    
    print(f"  😴 Rested for {hours} hours.")
    print(f"  ⚡ Energy restored to {resources.energy}/100")
    print(f"  ⏰ Time: {resources.get_time_string()}")


def daily_reset(game_state: GameState) -> None:
    """
    Reset daily resources and generate new content.
    
    Args:
        game_state: Current game state
    """
    # Restore some energy for new day
    game_state.resources.restore_energy(50)
    
    # Could generate new quests here
    print(f"\n  🌅 New day! Day {game_state.resources.current_day}")
    print(f"  ⚡ Energy refreshed to {game_state.resources.energy}/100\n")

