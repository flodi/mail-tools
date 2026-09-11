tell application "Mail"
    set sel to selection
    if (count of sel) is 0 then
        display notification "Nessuna email selezionata" with title "Todoist"
        return
    end if
    set theMessage to item 1 of sel
    set theSubject to subject of theMessage
    set theMessageID to message id of theMessage
end tell

set theLink to "message://%3C" & theMessageID & "%3E"

set encSubject to do shell script "/usr/bin/python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1]))' " & quoted form of theSubject
set encDesc to do shell script "/usr/bin/python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1]))' " & quoted form of theLink

do shell script "open 'todoist://openquickadd?content=" & encSubject & "&description=" & encDesc & "'"
