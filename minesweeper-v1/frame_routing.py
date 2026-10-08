"""Project-local negotiated routing with congestion history.
Based on the shared compiler router; game components and boundary pins stay fixed.
"""
from collections import defaultdict, deque
from heapq import heappop, heappush
import math
from placement_backend import Router, wire_cell, manhattan
from arrowasm import MapError, validate_cell

class CongestionRouting:
    def ripup_conflicts(self,net,path):
        """Preserve unaffected branches of a bus when repairing one collision."""
        cut={p for p in path if self.owners.get(p)==net and p not in self.fixed_cells}
        points={p for p in self.cells if self.owners.get(p)==net}
        # A flexible OR/BUF root is owned by "gate:<id>", not by its
        # output net. Its removed branch must also disappear from outs.
        root=self.roots[net]
        for p in points|{root}:
            if p in self.outs:self.outs[p].difference_update(cut)
        reachable=self.tree(net)
        removed={p for p in points if p not in self.fixed_cells and (p in cut or p not in reachable)}
        while removed:
            for p in removed:
                self.cells.pop(p,None);self.owners.pop(p,None);self.outs.pop(p,None)
            for p in (points-removed)|{root}:
                if p in self.outs:self.outs[p].difference_update(removed)
            points-=removed
            removed={p for p in points if p not in self.fixed_cells and not self.outs.get(p)}

    def path(self, tree, goal, margin, soft=False):
        lo_x, lo_y, hi_x, hi_y = self.bounds
        net = self.owners[goal]
        # An isolated sink otherwise makes forward A* flood the whole board.
        # Check a small reverse component first. Exceeding the budget means
        # "unknown", so a routable path is never rejected by this shortcut.
        seen,pending={goal},deque([goal])
        connected=goal in tree
        while pending and not connected and len(seen)<=128:
            current=pending.popleft()
            for dx,dy in ((1,0),(0,1),(-1,0),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)):
                for distance in ((1,) if dx and dy else (1,2)):
                    predecessor=current[0]+distance*dx,current[1]+distance*dy
                    if not self.route_allowed(predecessor):continue
                    if not (lo_x-margin<=predecessor[0]<=hi_x+margin and lo_y-margin<=predecessor[1]<=hi_y+margin):
                        continue
                    if predecessor in seen or predecessor in self.reserved:
                        continue
                    if predecessor in tree:
                        if predecessor in self.outs and len(self.outs[predecessor])<3 and wire_cell(predecessor,self.outs[predecessor]|{current}) is not None:
                            connected=True
                        continue
                    blocked=predecessor in self.cells
                    removable=soft and predecessor not in self.fixed_cells and self.owners.get(predecessor)!=net
                    if blocked and not removable:
                        continue
                    seen.add(predecessor);pending.append(predecessor)
        if not connected and not pending:
            return None
        heap, cost, previous = [], {}, {}
        for key in sorted(tree):
            if key in self.outs and len(self.outs[key]) < 3:
                cost[key] = 0
                heappush(heap, (manhattan(key, goal) / 2, 0, key))
        while heap:
            _, spent, key = heappop(heap)
            if spent != cost[key]:
                continue
            if key == goal:
                path = [key]
                while path[-1] in previous:
                    path.append(previous[path[-1]])
                return list(reversed(path))
            for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1)):
                for distance in ((1,) if dx and dy else (1, 2)):
                    next_key = key[0] + distance * dx, key[1] + distance * dy
                    if key in getattr(self,'flexible_gates',()) and next_key in self.pins[key]:continue
                    if not self.route_allowed(next_key):continue
                    if not (lo_x - margin <= next_key[0] <= hi_x + margin and lo_y - margin <= next_key[1] <= hi_y + margin):
                        continue
                    blocked = next_key in self.cells and next_key != goal
                    removable = soft and next_key not in self.fixed_cells and self.owners.get(next_key) != net
                    if next_key in self.reserved or (blocked and not removable):
                        continue
                    if key in tree and wire_cell(key, self.outs[key] | {next_key}) is None:
                        continue
                    added = 1 if distance == 1 and not (dx and dy) else 1.05
                    if blocked:
                        added += 20
                    added += self.routing_history.get(next_key, 0)
                    candidate = spent + added
                    if candidate < cost.get(next_key, math.inf):
                        cost[next_key], previous[next_key] = candidate, key
                        heappush(heap, (candidate + manhattan(next_key, goal) / 2, candidate, next_key))
        return None

    def route_phase(self,targets):
        self.routing_history = {}
        incremental=set()
        order=sorted((net for net,sinks in targets.items() if sinks),key=lambda net:(-len(targets[net]),net))
        mode=getattr(self,'routing_order','fanout')
        if mode in ('short','long'):
            sign=1 if mode=='short' else -1
            order.sort(key=lambda net:(sign*sum(manhattan(self.roots[net],p) for p in set(targets[net])),net))
        queue, attempts = deque(order), 0
        net_attempts=defaultdict(int)
        conflicts=defaultdict(int);last_goal={}
        def fail(message,net,goal=None):
            common=sorted(conflicts.items(),key=lambda e:-e[1])[:5]
            message+=f'; goal={goal or last_goal.get(net)}; conflicts={common}'
            error=MapError(message);error.net=net;error.goal=goal
            raise error
        while queue:
            net = queue.popleft()
            attempts += 1
            net_attempts[net] += 1
            # A few conflicting nets must not consume the entire graph's budget
            # by repeatedly tearing down each other's identical routes.
            limit=max(30,len(set(targets[net]))*12)
            if net_attempts[net] > limit:
                fail(f"Цепь {net} повторно конфликтует: исчерпан лимит {limit} перестроений",net)
            if attempts > max(40, len(order)*20):
                fail("Исчерпан бюджет перестройки проводов",net)
            if attempts%400==0:print(f'Routing progress: {attempts} repairs, {len(queue)} nets pending, {len(self.cells)} arrows',flush=True)
            # A retained trunk can force two nets to repair the same crossing
            # forever. Periodically release the whole trunk so congestion
            # history can choose a different topology, not just another leaf.
            if mode=='full' or net not in incremental or net_attempts[net]%3==0:self.clear_net(net)
            incremental.discard(net)
            tree=self.tree(net)
            pending=set(targets[net])-tree
            while pending:
                goal = min(pending, key=lambda p: (min(manhattan(p, start) for start in tree), p))
                last_goal[net]=goal
                path = None
                for margin in (3, 8, 16, 32):
                    path = self.path(tree, goal, margin)
                    if path:
                        break
                if path is None:
                    path = self.path(tree,goal,8,soft=True)
                    if path is None:
                        fail(f"Не удалось проложить компактную цепь {net}",net,goal)
                    blockers = sorted({self.owners[p] for p in path if p in self.cells and p not in self.fixed_cells and self.owners[p] != net})
                    for point in path:
                        if point in self.cells and point not in self.fixed_cells and self.owners.get(point) != net:
                            self.routing_history[point] = self.routing_history.get(point, 0) + 5
                    for blocker in blockers:
                        conflicts[(net,blocker)]+=1
                        self.ripup_conflicts(blocker,path)
                        incremental.add(blocker)
                        if blocker not in queue:
                            queue.append(blocker)
                        self.ripups += 1
                    path = self.path(tree,goal,32)
                    if path is None:
                        fail(f"Не удалось перестроить цепь {net}",net,goal)
                for key in path[1:-1]:
                    self.add(key, net)
                for key, target in zip(path, path[1:]):
                    self.outs[key].add(target)
                tree.update(path)
                pending.remove(goal)

    def route(self, order=None):
        if self.routing_strategy=='core_io':return Router.route(self,order)
        self.io_conflict_fallback = True
        self.route_phase(self.sinks)
        for key, targets in self.outs.items():
            if not targets:
                # Unused inputs still have a physical contact; emit only into empty
                # space that is also free of Source/Target fixture positions.
                for dx, dy in ((1, 0), (0, -1), (0, 1), (-1, 0)):
                    dest = key[0] + dx, key[1] + dy
                    if dest not in self.cells and dest not in self.reserved:
                        targets.add(dest)
                        break
                else:
                    raise MapError(f"Не удалось изолировать неиспользуемый контакт {key}")
            self.cells[key] = wire_cell(key, targets)
            if self.cells[key] is None:
                raise MapError(f"Неподдерживаемое разветвление в {key}")
        for key, cell in self.cells.items():
            validate_cell(*key, cell)
        self.validate()
        return self.cells
