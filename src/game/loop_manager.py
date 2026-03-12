from __future__ import annotations

from src.game.engine import GameEngine, TurnResult


class LoopManager:
    """High-level manager for the time loop lifecycle."""

    def __init__(self, engine: GameEngine):
        self.engine = engine
        self.is_game_active = False
        self.awaiting_loop_restart = False

    def start_new_game(self) -> TurnResult:
        result = self.engine.new_game()
        self.is_game_active = True
        self.awaiting_loop_restart = False
        return result

    def handle_input(self, player_input: str) -> TurnResult:
        if not self.is_game_active:
            return self.start_new_game()

        if self.awaiting_loop_restart:
            self.awaiting_loop_restart = False
            return self.engine.new_loop()

        result = self.engine.process_turn(player_input)

        if result.is_ending:
            if result.ending_id in ("sinking_into_the_deep", "sanity_break"):
                self.awaiting_loop_restart = True
            elif result.ending_id in ("the_seal_endures", "breaking_the_cycle"):
                self.is_game_active = False

        gs = self.engine.game_state
        if gs and gs.is_midnight and not result.is_ending:
            self.awaiting_loop_restart = True

        return result

    def force_restart_loop(self) -> TurnResult:
        self.awaiting_loop_restart = False
        return self.engine.new_loop()
