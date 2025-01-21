function C1M1_Tutorial01(owner)
	Tutorial01script = owner
	local MoveDone = 0
	local LookDone = 0
	EnableControllerItem(constant.CONTROL_TRANSFER, 0)
	EnableControllerItem(constant.CONTROL_HUD_TRANSFER, 0)
	EnableControllerItem(constant.CONTROL_NEXT_UNIT_TYPE, 0)
	EnableControllerItem(constant.CONTROL_PREV_UNIT_TYPE, 0)
	EnableControllerItem(constant.CONTROL_NEXT_UNIT, 0)
	EnableControllerItem(constant.CONTROL_PREV_UNIT, 0)
	SetObjectiveData(Objective.Look, constant.OBJECTIVE_DATA_VISIBLE, 0)
	SetObjectiveData(Objective.Watchtower, constant.OBJECTIVE_DATA_VISIBLE, 0)
	SetObjectiveData(Objective.Move, constant.OBJECTIVE_DATA_VISIBLE, 0)
	SetObjectiveData(Objective.FindSpy, constant.OBJECTIVE_DATA_VISIBLE, 0)
	SetObjectiveData(Objective.AlphaCompany, constant.OBJECTIVE_DATA_VISIBLE, 0)
	SetObjectiveData(Objective.AmmoDump, constant.OBJECTIVE_DATA_VISIBLE, 0)
	SetObjectiveData(Objective.Recon, constant.OBJECTIVE_DATA_VISIBLE, 0)
	while true do
		if C1M1_Global_Variable == 1 then
			break
		end
		EndFrame()
	end
	DebugOut("Show Small Controller")
	SetHudState(constant.HUD_CONTROLIMAGE_ALL, constant.HUD_ITEM_ON, 540, 380, 0.6)
	SetHudState(constant.HUD_CONTROLIMAGE_STICK, constant.HUD_ITEM_FLASH, 9999, 540, 380, 0.6)
	ClearMessageQueue()
	PhoneMessage(7, constant.ID_NONE, 0, 6, SpriteID.CO_WF_Betty_Happy)
	PhoneMessage(3, constant.ID_NONE, 0, 6, SpriteID.CO_WF_Betty_Happy)
	while true do
		if IsInArea(GetPlayerUnit(), Map_Zone.Movement) and C1M1_JumpDone == 0 then
			C1M1_JumpDone = 1
			SetHudState(constant.HUD_CONTROLIMAGE_STICK, constant.HUD_ITEM_OFF, 540, 380, 0.6)
			ClearMessageQueue()
			PhoneMessage(6, constant.ID_NONE, 0, 4, SpriteID.CO_WF_Betty_Happy)
			SetHudState(constant.HUD_CONTROLIMAGE_B, constant.HUD_ITEM_FLASH, 9999, 540, 380, 0.6)
		elseif IsInArea(GetPlayerUnit(), Map_Zone.Movement) and 1 <= C1M1_JumpDone then
		else
			EndFrame()
			while true do
				if IsInArea(GetPlayerUnit(), Map_Zone.Jump) then
					SetHudState(constant.HUD_CONTROLIMAGE_B, constant.HUD_ITEM_OFF, 540, 380, 0.6)
					Kill(Destroyable_Object.Gateopen0003)
					Vanish(Destroyable_Object.Gate0009)
					Vanish(Destroyable_Object.Gate0010)
					SetObjectiveData(Objective.Obstacles, constant.OBJECTIVE_DATA_STATE, 1)
					SetObjectiveData(Objective.Obstacles, constant.OBJECTIVE_DATA_VISIBLE, 0)
					SetObjectiveData(Objective_Marker.Objective_One_A, constant.OBJECTIVE_MARKER_DATA_VISIBLE, 0)
					SetObjectiveData(Objective_Marker.Objective_One_B, constant.OBJECTIVE_MARKER_DATA_VISIBLE, 1)
					SetObjectiveData(Objective.TargetDummy0, constant.OBJECTIVE_DATA_VISIBLE, 1)
					ClearMessageQueue()
					PhoneMessage(45, constant.ID_NONE, 0, 6, SpriteID.CO_WF_Betty_Happy)
				else
					EndFrame()
					while true do
						if DummiesDestroyed >= 5 then
							break
						end
						EndFrame()
					end
				end
			end
		end
	end
	SetObjectiveData(Objective.TargetDummy0, constant.OBJECTIVE_DATA_VISIBLE, 0)
	SetObjectiveData(Objective.TargetDummy1, constant.OBJECTIVE_DATA_VISIBLE, 0)
	SetObjectiveData(Objective.TargetDummy2, constant.OBJECTIVE_DATA_VISIBLE, 0)
	SetObjectiveData(Objective.TargetDummy3, constant.OBJECTIVE_DATA_VISIBLE, 0)
	SetObjectiveData(Objective.TargetDummy4, constant.OBJECTIVE_DATA_VISIBLE, 0)
	SetObjectiveData(Objective.TargetDummy5, constant.OBJECTIVE_DATA_STATE, 1)
	SetObjectiveData(Objective.TargetDummy5, constant.OBJECTIVE_DATA_VISIBLE, 0)
	SetObjectiveData(Objective_Marker.Objective_One_B, constant.OBJECTIVE_MARKER_DATA_VISIBLE, 0)
	SetObjectiveData(Objective_Marker.Objective_One_C, constant.OBJECTIVE_MARKER_DATA_VISIBLE, 1)
	local Timer = GetTime()
	while true do
		if IsInRectangle(GetPlayerUnit(), 500, 125, 840, 2000) and MoveDone == 0 then
			MoveDone = 1
			break
		end
		EndFrame()
	end
	ClearMessageQueue()
	PhoneMessage(109, constant.ID_NONE, 0, 8, SpriteID.CO_WF_Betty_Happy)
	DebugOut("Show Small Controller")
	SetHudState(constant.HUD_CONTROLIMAGE_SHOULDERR, constant.HUD_ITEM_FLASH, 9999, 540, 380, 0.6)
	SetHudState(constant.HUD_CONTROLIMAGE_STICK, constant.HUD_ITEM_FLASH, 9999, 540, 380, 0.6)
	SetObjectiveData(Objective_Marker.Objective_One_C, constant.OBJECTIVE_MARKER_DATA_VISIBLE, 0)
	SetObjectiveData(Objective_Marker.ObjectiveWatchtowerOne, constant.OBJECTIVE_MARKER_DATA_VISIBLE, 1)
	SetObjectiveData(Objective_Marker.ObjectiveWatchtowerTwo, constant.OBJECTIVE_MARKER_DATA_VISIBLE, 1)
	PhoneMessage(14, constant.ID_NONE, 0, 8, SpriteID.CO_WF_Betty_Happy)
	DebugOut("Invisible Sentry Buildings now active")
	SetActive(Building.WFsentry0001, constant.ACTIVE)
	SetActive(Building.WFsentry0002, constant.ACTIVE)
	SetObjectiveData(Objective.Watchtower, constant.OBJECTIVE_DATA_VISIBLE, 1)
	local Timer = GetTime()
	while true do
		if 0 < PlayerAngleToTarget(Building.WFsentry0001) and 4 > PlayerAngleToTarget(Building.WFsentry0001) then
			break
		end
		if 0 < PlayerAngleToTarget(Building.WFsentry0002) and 4 > PlayerAngleToTarget(Building.WFsentry0002) then
			break
		end
		if GetTargetedObject() == Building.WFsentry0001 or GetTargetedObject() == Building.WFsentry0002 then
			break
		end
		if GetTime() > Timer + 15 then
			PhoneMessage(14, constant.ID_NONE, 0, 8, SpriteID.CO_WF_Betty_Happy)
			DebugOut("Show Small Controller")
			SetHudState(constant.HUD_CONTROLIMAGE_SHOULDERR, constant.HUD_ITEM_FLASH, 9999, 540, 380, 0.6)
			SetHudState(constant.HUD_CONTROLIMAGE_STICK, constant.HUD_ITEM_FLASH, 9999, 540, 380, 0.6)
			Timer = GetTime()
			DebugOut("Tutorial 01b Timer = ", Timer, " seconds")
		end
		EndFrame()
	end
	DebugOut("Look Tutorial is complete")
	ControllerImageOn = 0
	DebugOut("Controller Image turned off!")
	DebugOut("Turn Off Flashing")
	SetHudState(constant.HUD_CONTROLIMAGE_SHOULDERR, constant.HUD_ITEM_OFF, 540, 380, 0.6)
	SetHudState(constant.HUD_CONTROLIMAGE_STICK, constant.HUD_ITEM_OFF, 540, 380, 0.6)
	SetHudState(constant.HUD_CONTROLIMAGE_ALL, constant.HUD_ITEM_OFF, 540, 380, 0.6)
	Kill(Destroyable_Object.Gateopen0005)
	Vanish(Destroyable_Object.Gate0001)
	Vanish(Destroyable_Object.Gate0002)
	if C1M1_Global_Variable == 1 then
		SetObjectiveData(Objective_Marker.Objective_One_C, constant.OBJECTIVE_MARKER_DATA_VISIBLE, 0)
		SetObjectiveData(Objective_Marker.ObjectiveWatchtowerOne, constant.OBJECTIVE_MARKER_DATA_VISIBLE, 0)
		SetObjectiveData(Objective_Marker.ObjectiveWatchtowerTwo, constant.OBJECTIVE_MARKER_DATA_VISIBLE, 0)
		SetObjectiveData(Objective_Marker.ObjectiveOne, constant.OBJECTIVE_MARKER_DATA_VISIBLE, 1)
		SetObjectiveData(Objective.Watchtower, constant.OBJECTIVE_DATA_STATE, 1)
		SetObjectiveData(Objective.Watchtower, constant.OBJECTIVE_DATA_VISIBLE, 0)
		SetObjectiveData(Objective.Move, constant.OBJECTIVE_DATA_VISIBLE, 1)
		ClearMessageQueue()
		PhoneMessage(9, constant.ID_NONE, 0, 8, SpriteID.CO_WF_Betty_Happy)
		PhoneMessage(10, constant.ID_NONE, 0, 8, SpriteID.CO_WF_Betty_Happy)
		WaitFor(1)
		SetHudState(constant.HUD_RADAR, constant.HUD_ITEM_ON)
	end
	local Timer = GetTime()
	while C1M1_Global_Variable == 1 do
		if GetTime() > Timer + 30 then
			PhoneMessage(10, constant.ID_NONE, 0, 8, SpriteID.CO_WF_Betty_Happy)
			Timer = GetTime()
		end
		EndFrame()
	end
	EndFrame()
	return
end
