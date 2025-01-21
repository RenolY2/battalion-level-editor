function C1M1_Tutorial04(owner)
	Tutorial04script = owner
	while true do
		if C1M1_SpyBalloons == 1 then
			break
		end
		EndFrame()
	end
	WaitFor(8)
	SetObjectiveData(Objective_Marker.ObjectiveTwo, constant.OBJECTIVE_MARKER_DATA_VISIBLE, 0)
	SetObjectiveData(Objective_Marker.ObjectiveThree, constant.OBJECTIVE_MARKER_DATA_VISIBLE, 1)
	DebugOut("Hi")
	while true do
		if IsInArea(GetPlayerUnit(), Map_Zone.Listening_Posts_2) then
			SetObjectiveData(Objective_Marker.ObjectiveTwo, constant.OBJECTIVE_MARKER_DATA_VISIBLE, 0)
			SetObjectiveData(Objective_Marker.ObjectiveThree, constant.OBJECTIVE_MARKER_DATA_VISIBLE, 0)
			SetObjectiveData(Objective_Marker.ObjectiveFour, constant.OBJECTIVE_MARKER_DATA_VISIBLE, 1)
			C1M1_Global_Variable = 6
			DebugOut("C1M1 Global Variable = ", C1M1_Global_Variable)
			
			while true do
				if IsInArea(GetPlayerUnit(), Map_Zone.Listening_Posts_3) then
					ClearMessageQueue()
					PhoneMessage(178, constant.ID_NONE, 0, 4, SpriteID.CO_WF_Betty_Sad)
					SetObjectiveData(Objective_Marker.ObjectiveFour, constant.OBJECTIVE_MARKER_DATA_VISIBLE, 0)
					SetObjectiveData(Objective_Marker.ObjectiveFourB, constant.OBJECTIVE_MARKER_DATA_VISIBLE, 1)
					C1M1_Global_Variable = 6
					DebugOut("C1M1 Global Variable = ", C1M1_Global_Variable)
					
					while true do
						if IsInArea(GetPlayerUnit(), Map_Zone.ObjectiveTwo) then
							ClearMessageQueue()
							PhoneMessage(115, constant.ID_NONE, 0, 4, SpriteID.CO_WF_Betty_Happy)
							break
						end
						EndFrame()
					end
					break
				else
					EndFrame()
				end
			end
			break
		else
			EndFrame()
		end
	end
	EndFrame()
	return
end
