local length = 256
local scale = 512
--Calculate log table
local logtbl = {}
for i = 1, length-1 do
	local x = math.log (i, 2)
	logtbl[i] = math.ceil (scale*x)
end
logtbl[0] = 0
--Write out the table
print ("short _logtbl[] =\n{")
local s = "\t"
for i = 0, length-1 do
	s = s .. string.format ("%5i", logtbl[i])
	if i < length-1 then
		s = s .. ","
	end
	if #s >= 68 then
		print (s)
		s = "\t"
	end
end
print (s)
print ("};")
--Calculate alog table
local algtbl = {}
local atl = 2*8*scale-1
for i = 0, atl do
	local x = i/scale
	algtbl[i] = math.floor (2^x)
end
--Write out the table
print ("short _algtbl[] =\n{")
local s = "\t"
for i = 0, atl do
	s = s .. string.format ("%5i", algtbl[i])
	if i < atl then
		s = s .. ","
	end
	if #s >= 68 then
		print (s)
		s = "\t"
	end
end
print (s)
print ("};")
--Test multiply
function multiply (a, b)
	if a ~= 0 and b ~= 0 then
		local x = logtbl[a]
		local y = logtbl[b]
		print (algtbl[x + y])
	else
		print (0)
	end
end
--Test divide
function divide (a, b)
	if a >= b then
		local x = logtbl[a]
		local y = logtbl[b]
		print (algtbl[x - y])
	else
		print (0)
	end
end

