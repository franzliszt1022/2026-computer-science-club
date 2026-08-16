"""
pathfinding.py
--------------
이 게임의 '수학 파트'가 모여 있는 모듈.

1) Grid            : 월드를 타일 그래프 G=(V,E)로 추상화
2) astar()         : 옥타일 휴리스틱을 쓰는 A* 최단경로
3) smooth_path()   : 가시선(line of sight) 판정으로 경로를 펴는 string pulling
4) FlowField       : 플레이어 1점에서 출발하는 다익스트라 → 전 타일 방향장
                     (A* 예산이 모자랄 때 쓰는 대체 경로)

수학 요약
---------
· 8방향 이동에서 직선 비용 1, 대각선 비용 √2일 때
      h(n) = (dx + dy) + (√2 - 2)·min(dx, dy)      [옥타일 거리]
  는 장애물이 없을 때의 정확한 최단거리이므로 실제 비용을 절대 넘지 않는다.
  → 허용적(admissible) ⇒ A*가 찾는 경로는 최단경로임이 보장된다.
· 또한 인접한 두 칸 n, n'에 대해 h(n) ≤ c(n, n') + h(n')이 성립한다(일관성).
  일관적이면 닫힌 목록에 한 번 들어간 노드를 다시 열 필요가 없어
  구현이 단순해지고 시간복잡도는 O(|E| log|V|)로 묶인다.
· string pulling은 삼각부등식 |AC| ≤ |AB| + |BC| 을 이용한다.
  A에서 C가 직접 보이면 중간점 B를 지우는 게 항상 이득이라서,
  경로 길이는 단조 감소하고 움직임이 '격자 계단' 티를 벗는다.
"""

import heapq
import math
from collections import deque

SQRT2 = math.sqrt(2.0)

# 8방향 이웃: (dx, dy, 비용)
_NEIGHBORS = [
    (1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
    (1, 1, SQRT2), (1, -1, SQRT2), (-1, 1, SQRT2), (-1, -1, SQRT2),
]


class Grid:
    """타일 단위 충돌 맵. solid[i] != 0 이면 벽."""

    def __init__(self, w, h, tile):
        self.w = w
        self.h = h
        self.tile = tile
        self.solid = bytearray(w * h)

    # --- 기본 질의 -------------------------------------------------
    def set_solid(self, tx, ty, v=1):
        if 0 <= tx < self.w and 0 <= ty < self.h:
            self.solid[ty * self.w + tx] = v

    def is_solid(self, tx, ty):
        if tx < 0 or ty < 0 or tx >= self.w or ty >= self.h:
            return True                      # 맵 밖은 벽 취급
        return self.solid[ty * self.w + tx] != 0

    def walkable(self, tx, ty):
        return not self.is_solid(tx, ty)

    def world_to_tile(self, x, y):
        return int(x // self.tile), int(y // self.tile)

    def tile_center(self, tx, ty):
        return (tx + 0.5) * self.tile, (ty + 0.5) * self.tile

    # --- 충돌/가시선 -----------------------------------------------
    def fits(self, x, y, r):
        """반지름 r인 원이 (x, y)에서 벽에 안 겹치는지 (네 모서리 근사)."""
        t = self.tile
        for ox, oy in ((-r, -r), (r, -r), (-r, r), (r, r)):
            if self.is_solid(int((x + ox) // t), int((y + oy) // t)):
                return False
        return True

    def ray_clear(self, x0, y0, x1, y1):
        """DDA(Amanatides & Woo) 격자 순회로 선분이 지나는 타일만 검사한다.

        선분을 잘게 쪼개 표본화하면 표본 간격에 따라 얇은 벽을 못 볼 수 있고
        계산량도 길이에 비례해 커진다. DDA는 '다음 세로선까지의 거리'와
        '다음 가로선까지의 거리'를 비교해 가까운 쪽으로만 한 칸 전진하므로,
        실제로 지나가는 타일 수(≈ dx+dy 칸)만큼만 검사하면 되고 누락도 없다.
        """
        t = self.tile
        w, h, solid = self.w, self.h, self.solid
        tx, ty = int(x0 // t), int(y0 // t)
        ex, ey = int(x1 // t), int(y1 // t)
        if tx < 0 or ty < 0 or tx >= w or ty >= h or solid[ty * w + tx]:
            return False
        if ex < 0 or ey < 0 or ex >= w or ey >= h or solid[ey * w + ex]:
            return False

        dx, dy = x1 - x0, y1 - y0
        inf = float("inf")
        if dx > 0:
            stepx, tdx, tmx = 1, t / dx, ((tx + 1) * t - x0) / dx
        elif dx < 0:
            stepx, tdx, tmx = -1, -t / dx, (tx * t - x0) / dx
        else:
            stepx, tdx, tmx = 0, inf, inf
        if dy > 0:
            stepy, tdy, tmy = 1, t / dy, ((ty + 1) * t - y0) / dy
        elif dy < 0:
            stepy, tdy, tmy = -1, -t / dy, (ty * t - y0) / dy
        else:
            stepy, tdy, tmy = 0, inf, inf

        for _ in range(512):
            if tmx < tmy:
                if tmx > 1.0:
                    return True
                tx += stepx
                tmx += tdx
            else:
                if tmy > 1.0:
                    return True
                ty += stepy
                tmy += tdy
            if tx < 0 or ty < 0 or tx >= w or ty >= h or solid[ty * w + tx]:
                return False
            if tx == ex and ty == ey:
                return True
        return True

    def line_clear(self, x0, y0, x1, y1, r=10.0):
        """반지름 r인 원이 통과할 수 있는가.
        중심선과, 좌우로 r만큼 평행이동한 두 선분까지 총 3개를 검사한다."""
        if not self.ray_clear(x0, y0, x1, y1):
            return False
        dx, dy = x1 - x0, y1 - y0
        d = math.hypot(dx, dy)
        if d < 1e-6 or r <= 0:
            return True
        # 진행 방향의 법선벡터 (-dy, dx)/|d| 에 r을 곱한 오프셋
        ox, oy = -dy / d * r, dx / d * r
        return (self.ray_clear(x0 + ox, y0 + oy, x1 + ox, y1 + oy) and
                self.ray_clear(x0 - ox, y0 - oy, x1 - ox, y1 - oy))

    def nearest_walkable(self, tx, ty, max_ring=8, radius=0.0):
        """(tx,ty)가 벽이면 BFS로 가장 가까운 빈 타일을 찾는다.
        radius를 주면 그 몸집이 설 수 있는 넓이의 칸만 고른다."""
        def ok(x, y):
            if not self.walkable(x, y):
                return False
            return radius <= 0 or self.fits_tile(x, y, radius)

        if ok(tx, ty):
            return tx, ty
        for rad in range(1, max_ring + 1):
            for oy in range(-rad, rad + 1):
                for ox in range(-rad, rad + 1):
                    if max(abs(ox), abs(oy)) != rad:
                        continue
                    if ok(tx + ox, ty + oy):
                        return tx + ox, ty + oy
        return None

    def flood_reachable(self, start):
        """start에서 갈 수 있는 타일 집합 (맵 생성 시 고립 지역 제거용)."""
        seen = {start}
        q = deque([start])
        while q:
            x, y = q.popleft()
            for dx, dy, _ in _NEIGHBORS:
                n = (x + dx, y + dy)
                if n not in seen and self.walkable(*n):
                    seen.add(n)
                    q.append(n)
        return seen

    # --- 통행 여유 공간 (clearance) ---------------------------------
    def build_clearance(self):
        """각 타일이 벽에서 몇 칸 떨어져 있는지를 미리 계산해 둔다.

        모든 벽 타일을 동시 출발점으로 삼는 다중 시작점 BFS(거리 변환).
        8방향을 같은 비용 1로 보므로 체비쇼프 거리가 나온다.
        `clear_d[t] = k` 라면 t를 중심으로 한 (2k-1)×(2k-1) 정사각형이 전부 빈칸이라는 뜻이고,
        따라서 t 중심에서 벽까지 최소 (k - 0.5) 타일의 여유가 있다.

        큰 적이 좁은 통로로 경로를 짜서 끼는 문제를 막기 위한 것.
        지형은 게임 중에 변하지 않으므로 맵 생성 직후 한 번만 계산하면 된다.
        """
        w, h = self.w, self.h
        INF = 1 << 30
        d = [INF] * (w * h)
        q = deque()
        for i in range(w * h):
            if self.solid[i]:
                d[i] = 0
                q.append(i)
        while q:
            i = q.popleft()
            cx, cy = i % w, i // w
            nd = d[i] + 1
            for dx, dy, _ in _NEIGHBORS:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < w and 0 <= ny < h:
                    ni = ny * w + nx
                    if nd < d[ni]:
                        d[ni] = nd
                        q.append(ni)
        self.clear_d = d
        return d

    def fits_tile(self, tx, ty, radius):
        """반지름 radius인 원이 (tx, ty) 타일 중심에 설 수 있는가."""
        if tx < 0 or ty < 0 or tx >= self.w or ty >= self.h:
            return False
        return (self.clear_d[ty * self.w + tx] - 0.5) * self.tile >= radius


def octile(ax, ay, bx, by):
    """옥타일 거리 휴리스틱 h(n)."""
    dx = abs(ax - bx)
    dy = abs(ay - by)
    return (dx + dy) + (SQRT2 - 2.0) * (dx if dx < dy else dy)


def astar(grid, start, goal, max_expand=2500, radius=0.0):
    """A* 최단경로. 타일 좌표 리스트(start 포함, goal 포함) 또는 None.

    radius를 주면 그 몸집이 지나갈 수 있는 폭의 칸만 통과한다.
    (탱커·보스처럼 큰 적이 1칸 통로로 경로를 짜서 끼는 것을 막는다.)

    넓은 길이 하나도 없으면 포기하는 대신 요구 폭을 낮춰 다시 찾는다.
    '돌아갈 수 있으면 돌아가고, 방법이 없으면 최선을 다해 간다'는 동작.
    """
    if radius > 0:
        for req in (radius, radius * 0.6, 0.0):
            path = _astar_core(grid, start, goal, max_expand, req)
            if path:
                return path
        return None
    return _astar_core(grid, start, goal, max_expand, 0.0)


def _astar_core(grid, start, goal, max_expand, radius):
    if start == goal:
        return [start]
    if grid.is_solid(*goal):
        fixed = grid.nearest_walkable(*goal)
        if fixed is None:
            return None
        goal = fixed

    # 출발점이나 목표가 이미 좁은 곳이면 여유 조건을 걸 수 없다(길이 아예 안 나옴).
    # 그럴 땐 조건을 풀고 일반 A*로 푼 뒤, 실제 이동에서 벽에 밀리며 빠져나오게 둔다.
    if radius > 0 and not (grid.fits_tile(*start, radius) and grid.fits_tile(*goal, radius)):
        radius = 0.0

    sx, sy = start
    gx, gy = goal
    open_heap = [(octile(sx, sy, gx, gy), 0.0, start)]
    came = {}
    gscore = {start: 0.0}
    closed = set()
    expanded = 0

    while open_heap:
        f, g, cur = heapq.heappop(open_heap)
        if cur in closed:
            continue
        if cur == goal:
            # 역추적
            path = [cur]
            while cur in came:
                cur = came[cur]
                path.append(cur)
            path.reverse()
            return path
        closed.add(cur)
        expanded += 1
        if expanded > max_expand:
            return None

        cx, cy = cur
        for dx, dy, cost in _NEIGHBORS:
            nx, ny = cx + dx, cy + dy
            if grid.is_solid(nx, ny):
                continue
            # 대각선으로 벽 모서리를 뚫고 지나가는 것 금지
            if dx and dy and (grid.is_solid(cx + dx, cy) or grid.is_solid(cx, cy + dy)):
                continue
            if radius > 0 and not grid.fits_tile(nx, ny, radius):
                continue                      # 몸집이 안 들어가는 좁은 칸은 제외
            nxt = (nx, ny)
            if nxt in closed:
                continue
            ng = g + cost
            if ng < gscore.get(nxt, 1e18):
                gscore[nxt] = ng
                came[nxt] = cur
                # h에 아주 작은 가중치를 더해 동점 상황에서 목표 쪽을 먼저 보게 한다
                # (여전히 h ≤ 실제비용이라 최적성은 유지)
                heapq.heappush(open_heap, (ng + octile(nx, ny, gx, gy) * 1.001, ng, nxt))
    return None


def smooth_path(grid, path, radius=10.0):
    """string pulling: 서로 직접 보이는 지점 사이의 중간 웨이포인트를 제거."""
    if not path or len(path) < 3:
        return path
    pts = [grid.tile_center(*t) for t in path]
    out = [pts[0]]
    i = 0
    n = len(pts)
    while i < n - 1:
        j = n - 1
        while j > i + 1:
            if grid.line_clear(pts[i][0], pts[i][1], pts[j][0], pts[j][1], radius):
                break
            j -= 1
        out.append(pts[j])
        i = j
    return out


class FlowField:
    """플레이어를 목표로 하는 단일 출발점 다익스트라 → 타일마다 '가야 할 방향'.

    A*는 개체마다 O(|E| log|V|)를 쓰지만, 목표가 모두 같으므로
    한 번의 다익스트라로 전 타일의 최적 방향을 뽑아 공유할 수 있다.
    대신 모두가 같은 길로 몰려 움직임이 단조로워지기 때문에,
    이 게임에서는 A* 계산 예산이 바닥났을 때의 '대체 경로'로만 쓴다.
    """

    def __init__(self, grid, max_dist=46.0):
        self.grid = grid
        self.n = grid.w * grid.h
        self.max_dist = max_dist          # 이 거리(타일) 밖은 계산하지 않는다
        self.dist = [1e18] * self.n
        self.dirs = [None] * self.n
        self._touched = []

    def rebuild(self, goal_tile):
        """단일 출발점 다익스트라. 딕셔너리 대신 평면 배열을 쓰고,
        직전 호출에서 건드린 칸만 초기화해 매 프레임 부담을 줄였다."""
        g = self.grid
        w, solid = g.w, g.solid
        goal = g.nearest_walkable(*goal_tile)
        dist, dirs = self.dist, self.dirs
        for i in self._touched:               # 이전 결과만 되돌린다 (전체 초기화 X)
            dist[i] = 1e18
            dirs[i] = None
        touched = self._touched = []
        if goal is None:
            return

        gi = goal[1] * w + goal[0]
        dist[gi] = 0.0
        touched.append(gi)
        heap = [(0.0, goal[0], goal[1])]
        push, pop = heapq.heappush, heapq.heappop
        limit = self.max_dist
        h_, w_ = g.h, w

        while heap:
            d, cx, cy = pop(heap)
            if d > dist[cy * w + cx] or d > limit:
                continue
            for dx, dy, cost in _NEIGHBORS:
                nx, ny = cx + dx, cy + dy
                if nx < 0 or ny < 0 or nx >= w_ or ny >= h_:
                    continue
                ni = ny * w + nx
                if solid[ni]:
                    continue
                if dx and dy and (solid[cy * w + nx] or solid[ny * w + cx]):
                    continue          # 벽 모서리를 대각선으로 통과 금지
                nd = d + cost
                if nd < dist[ni] and nd <= limit:
                    if dist[ni] > 1e17:
                        touched.append(ni)
                    dist[ni] = nd
                    inv = 0.70710678 if (dx and dy) else 1.0
                    dirs[ni] = (-dx * inv, -dy * inv)   # 이웃 → 현재 = 목표 방향
                    push(heap, (nd, nx, ny))

    def direction(self, tx, ty):
        if 0 <= tx < self.grid.w and 0 <= ty < self.grid.h:
            return self.dirs[ty * self.grid.w + tx]
        return None
