extends Node

signal gold_changed(new_gold)
signal lives_changed(new_lives)

var gold: int = 100
var lives: int = 20
var wave: int = 0

var enemies: Array = []

func add_gold(amount: int) -> void:
	gold += amount
	gold_changed.emit(gold)

func spend_gold(amount: int) -> bool:
	if gold >= amount:
		gold -= amount
		gold_changed.emit(gold)
		return true
	return false

func lose_life(amount: int = 1) -> void:
	lives -= amount
	lives_changed.emit(lives)
