extends Node2D

@export var range: float = 150.0
@export var fire_rate: float = 1.0
@export var damage: float = 5.0

var cooldown: float = 0.0
var bullet_scene := preload("res://scenes/Bullet.tscn")

func _ready() -> void:
	queue_redraw()

func _draw() -> void:
	draw_circle(Vector2.ZERO, 16, Color(0.2, 0.45, 0.9))

func _process(delta: float) -> void:
	cooldown -= delta
	if cooldown <= 0.0:
		var target := _find_target()
		if target:
			_shoot(target)
			cooldown = 1.0 / fire_rate

func _find_target() -> Node2D:
	var nearest: Node2D = null
	var nearest_dist: float = range
	for enemy in Game.enemies:
		if not is_instance_valid(enemy):
			continue
		var d: float = global_position.distance_to(enemy.global_position)
		if d <= range and d <= nearest_dist:
			nearest = enemy
			nearest_dist = d
	return nearest

func _shoot(target: Node2D) -> void:
	var bullet = bullet_scene.instantiate()
	get_tree().current_scene.add_child(bullet)
	bullet.global_position = global_position
	bullet.target = target
	bullet.damage = damage
