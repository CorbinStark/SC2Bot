from sc2 import BotAI, Race
import numpy
import sc2
from sc2 import Race, Difficulty
from sc2.player import Bot, Computer
from sc2.player import Human
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.unit import Unit
from sc2.units import Units
from sc2.position import Point2, Point3
from typing import Tuple, List

class CompetitiveBot(BotAI):
    NAME: str = "DefinitelyNotProxyRax"
    RACE: Race = Race.Terran

    def __init__(self):
        self.startCC = None
        self.iterationLastStimmed = 0

    def select_target(self) -> Point2:
        # Pick a random enemy structure's position
        targets = self.enemy_structures
        if targets:
            return targets.random.position

        # Pick a random enemy unit's position
        targets = self.enemy_units
        if targets:
            return targets.random.position

        # Pick enemy start location if it has no friendly units nearby
        if min([unit.distance_to(self.enemy_start_locations[0]) for unit in self.units]) > 5:
            return self.enemy_start_locations[0]

        # Pick a random mineral field on the map
        return self.mineral_field.random.position

    async def on_start(self):
        print("Game started")
        self.startCC = self.townhalls[0]
        # Do things here before the game starts

    async def on_step(self, iteration):
        CCs: Units = self.townhalls
        # If no command center exists, attack-move with all workers and cyclones
        if not CCs:
            #target = self.structures.random_or(self.enemy_start_locations[0]).position
            #for unit in self.workers | self.units(UnitTypeId.CYCLONE):
                #unit.attack(target)
            return
        else:
            # Otherwise, grab the first command center from the list of command centers
            cc: Unit = CCs.first

        # manage orbital energy and drop mules
        for oc in self.structures(UnitTypeId.ORBITALCOMMAND).filter(lambda x: x.energy >= 50):
            mfs = self.mineral_field.closer_than(10, oc)
            if mfs:
                mf = max(mfs, key=lambda x:x.mineral_contents)
                oc(AbilityId.CALLDOWNMULE_CALLDOWNMULE, mf)

        forces: Units = self.units(UnitTypeId.MARINE)
        medivacs: Units = self.units(UnitTypeId.MEDIVAC)
        targets = self.enemy_units + self.enemy_structures
        if targets:
            shouldStim = False
            if iteration - self.iterationLastStimmed > 35:
                shouldStim = True
                self.iterationLastStimmed = iteration

            for unit in forces:
                if iteration % 12 <= 1:
                    unit.move(targets.random.position)
                else:
                    if shouldStim and unit.health > 34:
                        unit(AbilityId.EFFECT_STIM_MARINE)
                    unit.attack(targets.random.position)
            for unit in medivacs:
                unit.attack(targets.random.position)

        # Every 50 iterations (here: every 50*8 = 400 frames)
        if iteration % 20 == 0:
            if len(self.units(UnitTypeId.MARINE)) > 62:
                target: Point2 = self.select_target()
                forces: Units = self.units(UnitTypeId.MARINE)
                medivacs: Units = self.units(UnitTypeId.MEDIVAC)
                # Every 4000 frames: send all forces to attack-move the target position
                if iteration % 20 == 0:
                    for unit in forces:
                        unit.attack(target)
                    for unit in medivacs:
                        unit.move(self.units(UnitTypeId.MARINE).random)
                # Every 400 frames: only send idle forces to attack the target position
                else:
                    for unit in forces.idle:
                        unit.attack(target)
            else:
                forces: Units = self.units(UnitTypeId.MARINE) + self.units(UnitTypeId.MEDIVAC)
                for unit in forces:
                    unit.move(CCs.first)

        my_scv = self.workers.random
        my_scv(AbilityId.TERRANBUILD_SUPPLYDEPOT)
        map_center = self.game_info.map_center

        for scv in self.workers.idle:
            scv.gather(self.mineral_field.closest_to(cc))

        depots: Units = self.structures(UnitTypeId.SUPPLYDEPOT)
        for depot in depots:
            depot(AbilityId.MORPH_SUPPLYDEPOT_LOWER)

        techlabs: Units = self.structures(UnitTypeId.BARRACKSTECHLAB)
        if len(self.structures(UnitTypeId.STARPORT)) > 0:
            for lab in techlabs:
                lab(AbilityId.RESEARCH_COMBATSHIELD)

        if self.supply_used > 58:
            for lab in techlabs:
                lab(AbilityId.BARRACKSTECHLABRESEARCH_STIMPACK)

        bays = self.structures(UnitTypeId.ENGINEERINGBAY)
        if len(bays) == 2:
            if bays[0].is_ready and bays[0].is_idle:
                bays[0](AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL1)
                bays[0](AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL2)
                bays[0](AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL3)
            if bays[1].is_ready and bays[1].is_idle:
                bays[1](AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL1)
                bays[1](AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL2)
                bays[1](AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL3)

        if self.supply_used > 43 and len(self.structures(UnitTypeId.ENGINEERINGBAY)) < 2 and len(self.structures(UnitTypeId.BARRACKS)) > 2:
            if self.can_afford(UnitTypeId.ENGINEERINGBAY):
                await self.build(UnitTypeId.ENGINEERINGBAY, near=cc.position.towards_with_random_angle(self.game_info.map_center, 3))

        if iteration == 30:
            await self.chat_send("glhf")

        if iteration == 170:
            await self.chat_send("I am not proxying you. Do not scout your third base location.")

        if iteration > 1000 and len(self.townhalls) < 2:
            await self.chat_send("Maybe I would have won if I did proxy :( :(")
            await self.chat_send("Self-destructing by dividing by 0")
            x = 5/0
            exit(0)

        if self.townhalls.ready.amount + self.already_pending(UnitTypeId.COMMANDCENTER) < 3 and self.supply_used > 18:
            if self.can_afford(UnitTypeId.COMMANDCENTER):
                await self.expand_now()

        if self.supply_used > 23 and cc.is_idle:
            cc.build(UnitTypeId.ORBITALCOMMAND)

        if len(CCs) > 1:
            await self.distribute_workers()

        # While we have less than 22 workers: build more
        # Check if we can afford them (by minerals and by supply)
        for base in CCs:
            if self.can_afford(UnitTypeId.SCV) and self.supply_workers + self.already_pending(UnitTypeId.SCV) < len(CCs)*19 and base.is_idle:
                base.train(UnitTypeId.SCV)

        # Build supply depots if we are low on supply, do not construct more than 2 at a time
        if self.supply_used < 25:
            if self.supply_left < 4:
                if self.can_afford(UnitTypeId.SUPPLYDEPOT) and self.already_pending(UnitTypeId.SUPPLYDEPOT) < 1:
                    # This picks a near-random worker to build a depot at location
                    # 'from command center towards game center, distance 8'
                    await self.build(UnitTypeId.SUPPLYDEPOT, near=cc.position.towards(self.game_info.map_center, 3))
        else:
            if self.supply_left < 12:
                if self.can_afford(UnitTypeId.SUPPLYDEPOT) and self.already_pending(UnitTypeId.SUPPLYDEPOT) < 2:
                    # This picks a near-random worker to build a depot at location
                    # 'from command center towards game center, distance 8'
                    await self.build(UnitTypeId.SUPPLYDEPOT, near=cc.position.towards(self.game_info.map_center, 12))

            # If we have at least one barracks that is compelted, build factory
            if self.structures(UnitTypeId.BARRACKS).ready:
                if self.structures(UnitTypeId.FACTORY).amount < 1 and not self.already_pending(UnitTypeId.FACTORY):
                    if self.can_afford(UnitTypeId.FACTORY):
                        position: Point2 = cc.position.towards_with_random_angle(self.game_info.map_center, 8)
                        await self.build(UnitTypeId.FACTORY, near=position)

        if len(CCs) > 1 and len(self.structures(UnitTypeId.STARPORT)) > 0:
            if len(self.structures(UnitTypeId.BARRACKS)) + len(self.structures(UnitTypeId.BARRACKSFLYING)) < 3:
                # If we can afford barracks
                if self.can_afford(UnitTypeId.BARRACKS):
                    # Near same command as above with the depot
                    await self.build(UnitTypeId.BARRACKS, near=cc.position.towards_with_random_angle(self.game_info.map_center, 5))

        if len(self.structures(UnitTypeId.FACTORY).ready) > 0 and len(self.structures(UnitTypeId.STARPORT)) + len(self.structures(UnitTypeId.STARPORTFLYING)) < 1:
            if self.can_afford(UnitTypeId.STARPORT):
                await self.build(UnitTypeId.STARPORT, near=cc.position.towards_with_random_angle(self.game_info.map_center, 6))

        if self.supply_used > 45 and len(self.structures(UnitTypeId.STARPORT)) > 0:
            if len(self.structures(UnitTypeId.BARRACKS)) + len(self.structures(UnitTypeId.BARRACKSFLYING)) < 5:
                # If we can afford barracks
                if self.can_afford(UnitTypeId.BARRACKS):
                    # Near same command as above with the depot
                    await self.build(UnitTypeId.BARRACKS, near=cc.position.towards_with_random_angle(self.game_info.map_center, 7))

            if len(self.structures(UnitTypeId.BARRACKS)) + len(self.structures(UnitTypeId.BARRACKSFLYING)) < 20:
                # If we can afford barracks
                if self.can_afford(UnitTypeId.COMMANDCENTER):
                    # Near same command as above with the depot
                    await self.build(UnitTypeId.BARRACKS, near=cc.position.towards_with_random_angle(self.game_info.map_center, 5))
                    await self.build(UnitTypeId.SUPPLYDEPOT, near=cc.position.towards_with_random_angle(self.game_info.map_center, 15))

        # If we have supply depots (careful, lowered supply depots have a different UnitTypeId: UnitTypeId.SUPPLYDEPOTLOWERED)
        if self.structures(UnitTypeId.SUPPLYDEPOTLOWERED):
            # If we have no barracks
            if len(self.structures(UnitTypeId.BARRACKS)) < 1:
                # If we can afford barracks
                if self.can_afford(UnitTypeId.BARRACKS):
                    # Near same command as above with the depot
                    await self.build(UnitTypeId.BARRACKS, near=cc.position.towards(self.game_info.map_center, 4))

            # If we have a barracks (complete or under construction) and less than 2 gas structures (here: refineries)
            elif self.structures(UnitTypeId.BARRACKS) and ((self.gas_buildings.amount < 1) or (self.supply_used > 21 and self.gas_buildings.amount < 2) or (self.supply_used > 39 and self.gas_buildings.amount < 3)):
                if self.can_afford(UnitTypeId.REFINERY):
                    # All the vespene geysirs nearby, including ones with a refinery on top of it
                    vgs = self.vespene_geyser.closer_than(5, self.startCC)
                    for vg in vgs:
                        if self.gas_buildings.filter(lambda unit: unit.distance_to(vg) < 1):
                            continue
                        # Select a worker closest to the vespene geysir
                        worker: Unit = self.select_build_worker(vg)
                        # Worker can be none in cases where all workers are dead
                        # or 'select_build_worker' function only selects from workers which carry no minerals
                        if worker is None:
                            continue
                        # Issue the build command to the worker, important: vg has to be a Unit, not a position
                        worker.build_gas(vg)
                        # Only issue one build geysir command per frame
                        break

                # If we have at least one barracks that is compelted, build factory
            if self.structures(UnitTypeId.BARRACKS).ready and len(CCs) > 1:
                if self.structures(UnitTypeId.FACTORY).amount + self.structures(UnitTypeId.FACTORYFLYING).amount < 1:
                    if self.can_afford(UnitTypeId.FACTORY):
                        position: Point2 = cc.position.towards_with_random_angle(self.game_info.map_center, 4)
                        await self.build(UnitTypeId.FACTORY, near=position)

        def factory_points_to_build_addon(sp_position: Point2) -> List[Point2]:
            """ Return all points that need to be checked when trying to build an addon. Returns 4 points. """
            addon_offset: Point2 = Point2((2.5, -0.5))
            addon_position: Point2 = sp_position + addon_offset
            addon_points = [
                (addon_position + Point2((x - 0.5, y - 0.5))).rounded for x in range(0, 2) for y in range(0, 2)
            ]
            return addon_points

        sp: Unit
        if len(CCs) > 1:
            for sp in self.structures(UnitTypeId.BARRACKS).ready.idle:
                if not sp.has_add_on and self.can_afford(UnitTypeId.BARRACKSREACTOR):
                    addon_points = factory_points_to_build_addon(sp.position)
                    if all(
                            self.in_map_bounds(addon_point)
                            and self.in_placement_grid(addon_point)
                            and self.in_pathing_grid(addon_point)
                            for addon_point in addon_points
                    ):
                        if len(self.structures(UnitTypeId.BARRACKSTECHLAB)) < 1:
                            sp.build(UnitTypeId.BARRACKSTECHLAB)
                        else:
                            sp.build(UnitTypeId.BARRACKSREACTOR)
                    else:
                        sp(AbilityId.LIFT)

        def factory_land_positions(sp_position: Point2) -> List[Point2]:
            """ Return all points that need to be checked when trying to land at a location where there is enough space to build an addon. Returns 13 points. """
            land_positions = [(sp_position + Point2((x, y))).rounded for x in range(-1, 2) for y in range(-1, 2)]
            return land_positions + factory_points_to_build_addon(sp_position)

        # Find a position to land for a flying starport so that it can build an addon
        for sp in self.structures(UnitTypeId.BARRACKSFLYING).idle:
            possible_land_positions_offset = sorted(
                (Point2((x, y)) for x in range(-10, 10) for y in range(-10, 10)),
                key=lambda point: point.x ** 2 + point.y ** 2,
            )
            offset_point: Point2 = Point2((-0.5, -0.5))
            possible_land_positions = (sp.position.rounded + offset_point + p for p in possible_land_positions_offset)
            for target_land_position in possible_land_positions:
                land_and_addon_points: List[Point2] = factory_land_positions(target_land_position)
                if all(
                        self.in_map_bounds(land_pos) and self.in_placement_grid(land_pos) and self.in_pathing_grid(land_pos)
                        for land_pos in land_and_addon_points
                ):
                    sp(AbilityId.LAND, target_land_position)
                    break

        #STARPORT FLYING
        sp: Unit
        if len(CCs) > 1:
            for sp in self.structures(UnitTypeId.STARPORT).ready.idle:
                if not sp.has_add_on and self.can_afford(UnitTypeId.STARPORTREACTOR):
                    addon_points = factory_points_to_build_addon(sp.position)
                    if all(
                            self.in_map_bounds(addon_point)
                            and self.in_placement_grid(addon_point)
                            and self.in_pathing_grid(addon_point)
                            for addon_point in addon_points
                    ):
                        sp.build(UnitTypeId.STARPORTREACTOR)
                    else:
                        sp(AbilityId.LIFT)

        # Find a position to land for a flying starport so that it can build an addon
        for sp in self.structures(UnitTypeId.STARPORTFLYING).idle:
            possible_land_positions_offset = sorted(
                (Point2((x, y)) for x in range(-10, 10) for y in range(-10, 10)),
                key=lambda point: point.x ** 2 + point.y ** 2,
            )
            offset_point: Point2 = Point2((-0.5, -0.5))
            possible_land_positions = (sp.position.rounded + offset_point + p for p in possible_land_positions_offset)
            for target_land_position in possible_land_positions:
                land_and_addon_points: List[Point2] = factory_land_positions(target_land_position)
                if all(
                        self.in_map_bounds(land_pos) and self.in_placement_grid(land_pos) and self.in_pathing_grid(land_pos)
                        for land_pos in land_and_addon_points
                ):
                    sp(AbilityId.LAND, target_land_position)
                    break

        # Show where it is flying to and show grid
        unit: Unit
        for sp in self.structures(UnitTypeId.BARRACKSFLYING).filter(lambda unit: not unit.is_idle):
            if isinstance(sp.order_target, Point2):
                p: Point3 = Point3((*sp.order_target, self.get_terrain_z_height(sp.order_target)))
                self.client.debug_box2_out(p, color=Point3((255, 0, 0)))

        for barracks in self.structures(UnitTypeId.BARRACKS).ready:
            # Reactor allows us to build two at a time
            if self.can_afford(UnitTypeId.MARINE) and self.already_pending(UnitTypeId.MARINE) < (len(self.structures(UnitTypeId.BARRACKS).ready) + len(self.structures(UnitTypeId.BARRACKSREACTOR))):
                barracks.train(UnitTypeId.MARINE)

        for starport in self.structures(UnitTypeId.STARPORT).ready:
            # Reactor allows us to build two at a time
            if self.can_afford(UnitTypeId.MEDIVAC) and self.already_pending(UnitTypeId.MEDIVAC) < 2:
                starport.train(UnitTypeId.MEDIVAC)

        # Saturate gas
        for refinery in self.gas_buildings:
            if refinery.assigned_harvesters < refinery.ideal_harvesters:
                worker: Units = self.workers.closer_than(10, refinery)
                if worker:
                    worker.random.gather(refinery)

        pass

    def on_end(self, result):
        print("Game ended.")
        # Do things here after the game ends
