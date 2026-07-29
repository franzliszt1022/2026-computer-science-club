extends Node2D

@export var wave_size: int = 5
@export var spawn_interval: float = 0.8
@export var time_between_waves: float = 5.0
@export var tower_cost: int = 20

var enemy_scene := preload("res://scenes/Enemy.tscn")
var tower_scene := preload("res://scenes/Tower.tscn")

var enemies_to_spawn: int = 0

@onready var path: Path2D = $Path2D
@onready var spawn_timer: Timer = $SpawnTimer
@onready var wave_timer: Timer = $WaveTimer
@onready var gold_label: Label = $UI/GoldLabel
@onready var lives_label: Label = $UI/LivesLabel
@onready var wave_label: Label = $UI/WaveLabel

func _ready() -> void:
	Game.gold_changed.connect(_on_gold_changed)
	Game.lives_changed.connect(_on_lives_changed)
	spawn_timer.timeout.connect(_on_spawn_timer_timeout)
	spawn_timer.one_shot = false
	wave_timer.timeout.connect(_on_wave_timer_timeout)
	wave_timer.one_shot = true
	_update_labels()
	queue_redraw()
	wave_timer.start(2.0)

func _draw() -> void:
	var points := path.curve.get_baked_points()
	for i in range(points.size() - 1):
		draw_line(points[i], points[i + 1], Color(0.5, 0.5, 0.5), 40.0)

func _on_wave_timer_timeout() -> void:
	_start_wave()

func _start_wave() -> void:
	Game.wave += 1
	wave_label.text = "Wave: %d" % Game.wave
	enemies_to_spawn = wave_size + (Game.wave - 1) * 2
	spawn_timer.start(spawn_interval)

func _on_spawn_timer_timeout() -> void:
	_spawn_enemy()
	enemies_to_spawn -= 1
	if enemies_to_spawn <= 0:
		spawn_timer.stop()
		wave_timer.start(time_between_waves)

func _spawn_enemy() -> void:
	var path_follow := PathFollow2D.new()
	path_follow.rotates = false
	path_follow.loop = false
	path.add_child(path_follow)
	var enemy = enemy_scene.instantiate()
	path_follow.add_child(enemy)
	enemy.path_follow = path_follow
	var extra_hp: float = (Game.wave - 1) * 4
	enemy.max_health += extra_hp
	enemy.health = enemy.max_health

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		_try_place_tower(get_global_mouse_position())

func _try_place_tower(pos: Vector2) -> void:
	if Game.spend_gold(tower_cost):
		var tower = tower_scene.instantiate()
		add_child(tower)
		tower.global_position = pos

func _on_gold_changed(new_gold: int) -> void:
	gold_label.text = "Gold: %d" % new_gold

func _on_lives_changed(new_lives: int) -> void:
	lives_label.text = "Lives: %d" % new_lives
	if new_lives <= 0:
		get_tree().paused = true
		print("Game Over")

func _update_labels() -> void:
	gold_label.text = "Gold: %d" % Game.gold
	lives_label.text = "Lives: %d" % Game.lives
	wave_label.text = "Wave: %d" % Game.wave
