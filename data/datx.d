import std.stdio;
import std.conv;
import std.file;
import std.stdint;
import std.path;

/*
top 8 bits is probably a file type id, or at least it seems that way. it's
the best I got at this point

1090 = images
1006 = geometry
1677 = alt. geometry
6030 = sounds
1627 = sounds
1107 = unknown. zlib'd data?
2013 = unknown
3355 = unknown
6710 = unknown. bind pose?
8388 = unknown. float heavy.

Most of these are probably uninteresting.
they're only a few bytes each and usually less than 1k
but nether the less:

5033 = unknown
4865 = unknown
5200 = unknown
5368 = unknown
6710 = unknown
6878 = unknown
7046 = unknown
8053 = unknown
8220 = unknown
9227 = unknown
9563 = unknown
1073 = unknown
1191 = unknown
1862 = unknown
1879 = unknown
2164 = unknown
4294 = unknown
*/

struct Header
{
	ubyte[300] pad;
	uint32_t magick;
	uint32_t page;
	uint32_t size;
	uint32_t unk1;
	uint32_t key;
	uint32_t unk2;
	uint32_t unk3;
	uint32_t unk4;
	uint32_t manifest;
}
struct Dir
{
	uint32_t[62] links;
	uint32_t num;
}
struct Entry
{
	uint32_t id;
	uint32_t offset;
	uint32_t unk1;
	uint32_t unk2;
}

void main (string[] args)
{
	string prefix = "";
	ubyte[] getdata (FILE *fp, ubyte[] page)
	{
		ubyte[] res;
		uint32_t jmp;
		do
		{
			fread (page.ptr, 1, page.length, fp);
			jmp = *(cast (uint32_t *)(page[0 .. 4].ptr));
			res ~= page[4 .. $];
		}
		while (jmp != 0);
		return res;
	}
	void parsedir (FILE *fp, ubyte[] page)
	{
		auto data = getdata (fp, page).dup;
		Dir *dir = cast (Dir *)data.ptr;
		Entry *ents = cast (Entry *)(data.ptr + (*dir).sizeof);	
		writefln ("Num files: %s", cast (uint)dir.num);
		for (auto i = 0; i < dir.num; i++)
		{
			/*
			writefln ("%s: %s %s %s %s",
				i,
				cast (uint)ents[i].id,
				cast (uint)ents[i].offset,
				cast (uint)ents[i].unk1,
				cast (uint)ents[i].unk2
			);
			*/
			string name = prefix ~ "/" ~ to!string (cast (uint)ents[i].id);
			fseek (fp, ents[i].offset, SEEK_SET);
			auto bin = getdata (fp, page);
			switch (ents[i].id>>24)
			{
			case 36: //Directmusic... lol
				auto f = File (name ~ ".music", "wb");
				auto size = *(cast (uint32_t *)bin[4 .. $].ptr);
				f.rawWrite (bin[8 .. size]);
				break;
			case 97: //PCM wave
				auto f = File (name ~ ".wav", "wb");
				auto size = *(cast (uint32_t *)bin[4 .. $].ptr);
				f.rawWrite (bin[8 .. size]);
				break;
			case 65: //Images
			default:
				//auto f = File (name ~ ".bin", "wb");
				//f.rawWrite (bin[4 .. $]);
				break;
			}
			
		}
		//Recurse
		for (auto i = 0; i < dir.links.length; i++)
		{
			auto link = dir.links[i];
			if (0 == link)
			{
				break;
			}
			fseek (fp, link, SEEK_SET);
			parsedir (fp, page);
		}
	}
	Header h;
	if (args.length < 2)
	{
		writeln ("datx <dat>");
		return;
	}
	auto _f = File (args[1], "rb");
	auto fp = _f.getFP ();
	//Create directory
	prefix = stripExtension (args[1]);
	mkdirRecurse (prefix);
	//Read the header and allocate page buffer
	fread (&h, 1, h.sizeof, fp);
	auto buf = new ubyte[h.page];
	writefln ("%s %s", h.page, h.manifest);
	//Dump the files
	fseek (fp, h.manifest, SEEK_SET);
	parsedir (fp, buf);
}