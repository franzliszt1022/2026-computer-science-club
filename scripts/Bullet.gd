extends Node2D

var target: Node2D
var speed: float = 400.0
var damage: float = 5.0

func _draw() -> void:
	draw_circle(Vector2.ZERO, 4, Color(1.0, 0.9, 0.2))

func _process(delta: float) -> void:
	if not is_instance_valid(target):
		queue_free()
		return
	var dir: Vector2 = target.global_position - global_position
	if dir.length() <= 8.0:
		target.take_damage(damage)
		queue_free()
		return
	global_position += dir.normalized() * speed * delta
