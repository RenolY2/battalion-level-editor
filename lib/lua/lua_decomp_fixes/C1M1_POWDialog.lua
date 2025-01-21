function C1M1_POWDialog(owner)
	local Timer = 0
	while true do
		if IsInArea(GetPlayerUnit(), Map_Zone.POW) and C1M1_POWs_Freed == 0 then
			do
				ClearMessageQueue()
				PhoneMessage(190, constant.ID_NONE, 0, 6, SpriteID.CO_WF_Betty_Happy)
				PhoneMessage(64, constant.ID_NONE, 0, 6, SpriteID.CO_WF_Betty_Happy)
				local Timer = GetTime()
			end
		elseif IsDead(Troop.TammoDumpGuard0001) and IsDead(Troop.TammoDumpGuard0002) and C1M1_POWs_Freed == 0 then
			do
				ClearMessageQueue()
				PhoneMessage(190, constant.ID_NONE, 0, 6, SpriteID.CO_WF_Betty_Happy)
				PhoneMessage(64, constant.ID_NONE, 0, 6, SpriteID.CO_WF_Betty_Happy)
				local Timer = GetTime()
			end
		else
			EndFrame()
			while true do
				if C1M1_POWs_Freed == 0 and GetTime() > Timer + 30 then
					ClearMessageQueue()
					PhoneMessage(190, constant.ID_NONE, 0, 4, SpriteID.CO_WF_Betty_Happy)
					PhoneMessage(64, constant.ID_NONE, 0, 4, SpriteID.CO_WF_Betty_Happy)
					Timer = GetTime()
					DebugOut("Tutorial 09d Timer = ", Timer, " seconds")
				end
				EndFrame()
			end
		end
	end
	EndFrame()
	return
end
