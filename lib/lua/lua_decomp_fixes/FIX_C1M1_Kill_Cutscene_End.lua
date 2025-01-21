function C1M1_Kill_Cutscene_End(owner)
	WaitFor(1)
	while true do
		if C1M1_Global_Variable >= 12 then
			WaitFor(5)
			DebugOut("End cutscene is skippable now")
			while true do
				if GetCurrentMissionAttempted() == true and (ReadControllerState(constant.CONTROL_SKIP_CUTSCENE, constant.CONTROL_JUST_PRESSED) or ReadControllerState(constant.CONTROL_SKIP_CUTSCENE_ALT, constant.CONTROL_JUST_PRESSED)) then
					DebugOut("Killed cutscene End", cutsceneEnd)
					Kill(cutsceneEnd)
					ClearMessageQueue()
					C1M1_Global_Variable = 13
					DebugOut("C1M1 Global Variable = ", C1M1_Global_Variable)
					cutsceneEnd = 1
					break
				end
				EndFrame()
			end
		else
			EndFrame()
		end
	end
	EndFrame()
	return
end
