function C1M1_Tutorial06(owner)
	Despawn(Troop.Tspy0003)
	while true do
		if IsInArea(GetPlayerUnit(), Map_Zone.Slope) then
			SetObjectiveData(Objective_Marker.ObjectiveFourB, constant.OBJECTIVE_MARKER_DATA_VISIBLE, 0)
			SetObjectiveData(Objective_Marker.DeadGrunt, constant.OBJECTIVE_MARKER_DATA_VISIBLE, 1)
			Despawn(Air_Vehicle.Entity0006)
			Despawn(Air_Vehicle.Entity0007)
			Despawn(Air_Vehicle.Entity0008)
			Despawn(Ground_Vehicle.Entity0000)
			Despawn(Ground_Vehicle.Entity0001)
			Despawn(Troop.Entity0031)
			Despawn(Troop.Entity0038)
			Despawn(Troop.Entity0039)
			Despawn(Troop.Entity0040)
			Despawn(Troop.Entity0044)
			Despawn(Troop.Entity0045)
			Despawn(Troop.Entity0046)
			Despawn(Troop.Entity0050)
			Despawn(Troop.Entity0051)
			Despawn(Troop.Entity0052)
			Despawn(Troop.Entity0053)
			Despawn(Troop.Entity0054)
			Despawn(Troop.Entity0055)
			Despawn(Troop.Entity0056)
			PhoneMessage(180, constant.ID_NONE, 0, 8, SpriteID.CO_WF_Betty_Happy)
			break
		end
		EndFrame()
	end
	local Timer = GetTime()
	while true do
		if IsInArea(GetPlayerUnit(), Map_Zone.Grunt) then
			ClearMessageQueue()
			PhoneMessage(36, constant.ID_NONE, 0, 4, SpriteID.CO_WF_Betty_Happy)
		else
			EndFrame()
			while true do
				if IsInArea(GetPlayerUnit(), Map_Zone.DeadGrunt) then
					ClearMessageQueue()
					PhoneMessage(37, constant.ID_NONE, 0, 4, SpriteID.CO_WF_Betty_Sad)
					SetObjectiveData(Objective_Marker.DeadGrunt, constant.OBJECTIVE_MARKER_DATA_VISIBLE, 0)
					SetObjectiveData(Objective.AlphaCompany, constant.OBJECTIVE_DATA_VISIBLE, 1)
					Spawn(Troop.Tspy0003)
				else
					EndFrame()
					while true do
						if IsInRectangle(GetPlayerUnit(), 465, 220, 550, 1500) then
							C1M1_Global_Variable = 7
							DebugOut("C1M1 Global Variable = ", C1M1_Global_Variable)
							PhoneMessage(38, constant.ID_NONE, 0, 4, SpriteID.CO_WF_Betty_Happy)
							break
						end
						EndFrame()
					end
				end
			end
		end
	end
	SetObjectiveData(Objective_Marker.ObjectiveSix, constant.OBJECTIVE_MARKER_DATA_VISIBLE, 1)
	return
end
