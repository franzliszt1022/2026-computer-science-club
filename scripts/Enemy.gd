extends Node2D

var speed: float = 80.0
var max_health: float = 10.0
var health: float = 10.0
var reward: int = 5
var path_follow: PathFollow2D

func _ready() -> void:
	health = max_health
	Game.enemies.append(self)
	queue_redraw()

func _process(delta: float) -> void:
	path_follow.progress += speed * delta
	queue_redraw()
	if path_follow.progress_ratio >= 1.0:
		_reach_end()

func _draw() -> void:
	draw_circle(Vector2.ZERO, 12, Color(0.85, 0.2, 0.2))
	var bar_width := 24.0
	var pct: float = clamp(health / max_health, 0.0, 1.0)
	draw_rect(Rect2(-bar_width / 2, -22, bar_width, 4), Color(0.2, 0.2, 0.2))
	draw_rect(Rect2(-bar_width / 2, -22, bar_width * pct, 4), Color(0.2, 0.9, 0.2))

func take_damage(amount: float) -> void:
	health -= amount
	if health <= 0.0:
		_die()

func _die() -> void:
	Game.add_gold(reward)
	_cleanup()

func _reach_end() -> void:
	Game.lose_life(1)
	_cleanup()

func _cleanup() -> void:
	Game.enemies.erase(self)
	if is_instance_valid(path_follow):
		path_follow.queue_free()
