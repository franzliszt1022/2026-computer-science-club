"""
ui.py — 마우스 버튼 공용 헬퍼
-----------------------------
game.py는 지금까지 100% 키보드 입력(on_key)만 처리했다. 메인메뉴/상점/설정/
레벨업 선택처럼 앞으로 만들 화면은 전부 "버튼 누르기"가 필요하므로, 여기서는
버튼 하나의 최소 단위(사각형 히트박스 + 식별자 + hover 판정)만 제공한다.
실제 그리기는 화면마다 디자인이 다르므로 각 draw_* 메서드가 알아서 한다.

좌표계 문제
-----------
game.py는 고정 논리 해상도(SW x SH)의 self.screen에 그린 뒤, present_frame()에서
실제 창 크기(self.display)에 맞춰 비율을 유지한 채 확대/레터박싱한다.
pygame.mouse.get_pos()나 MOUSEBUTTONDOWN 이벤트의 pos는 "실제 창" 좌표이므로,
버튼의 논리 좌표 rect와 비교하기 전에 반드시 screen_to_logical()로 역변환해야 한다.
"""

import pygame


def screen_to_logical(pos, display_size, logical_size):
    dw, dh = display_size
    sw, sh = logical_size
    if (dw, dh) == (sw, sh):
        return pos
    scale = min(dw / sw, dh / sh)
    out_w, out_h = sw * scale, sh * scale
    off_x, off_y = (dw - out_w) / 2, (dh - out_h) / 2
    return ((pos[0] - off_x) / scale, (pos[1] - off_y) / scale)


class Button:
    """사각형 히트박스 + hover 상태만 들고 있는 최소 단위. 그리기는 호출부 책임."""

    __slots__ = ("rect", "id", "hover")

    def __init__(self, x, y, w, h, id):
        self.rect = pygame.Rect(x, y, w, h)
        self.id = id
        self.hover = False

    def update_hover(self, logical_pos):
        self.hover = logical_pos is not None and self.rect.collidepoint(logical_pos)

    def hit(self, logical_pos):
        return logical_pos is not None and self.rect.collidepoint(logical_pos)
