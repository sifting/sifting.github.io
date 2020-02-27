--This script generates a table for use in a fast multiplication algorithm
--The table is computed for the function f(x) = (x^2)/4 for how ever many xs
--At the end of the script is a sample implementation of the algorithm.
--Generate table
tbl = {}
for i = 0, 511 do
	local a = i
	if i >= 256 then 
		a = i - 512
	end
	local x = math.floor (a*a/4)
	tbl[i] = x
end
--Write out the table
print ("short _multbl[] =\n{")
local s = "\t"
for i = 0, 511 do
	s = s .. string.format ("%5i", tbl[i])
	if i < 511 then
		s = s .. ","
	end
	if #s >= 68 then
		print (s)
		s = "\t"
	end
end
print (s)
print ("};")
--Implements multiplication by this formula: a*b = f(a + b) - f(a - b)
--A and B must be -128 <= x <= 127
function multiply (a, b)
	local x = bit32.extract (a + b, 0, 9)
	local y = bit32.extract (a - b, 0, 9)
	print (tbl[x] - tbl[y])
end
