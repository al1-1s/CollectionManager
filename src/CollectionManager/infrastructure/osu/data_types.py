from construct import (
    Adapter,
    Byte,
    Computed,
    Double,
    Float32l,
    IfThenElse,
    Int32ul,
    PascalString,
    Struct,
    VarInt,
    this,
    Int16ul,
    Int64ul,
    Float64l,
)

Uleb128 = VarInt
Int = Int32ul
Short = Int16ul
Long = Int64ul
Single = Float32l
Double = Float64l


class BooleanAdapter(Adapter):
    def _encode(self, obj, context, path):
        return 0x01 if obj else 0x00

    def _decode(self, obj, context, path):
        return obj != 0


Boolean = BooleanAdapter(Byte)


class OsuStringAdapter(Adapter):
    def _encode(self, obj, context, path):
        return {"marker": 0x0B if obj else 0x00, "value": obj}

    def _decode(self, obj, context, path):
        return obj.value


String = OsuStringAdapter(
    Struct(
        "marker" / Byte,
        "value"
        / IfThenElse(this.marker == 0x0B, PascalString(Uleb128, "utf8"), Computed("")),
    )
)


class IntFloatPairAdapter(Adapter):
    def _encode(self, obj, context, path):
        int_value, float_value = obj
        return {
            "int_marker": 0x08,
            "int_value": int_value,
            "float_marker": 0x0C,
            "float_value": float_value,
        }

    def _decode(self, obj, context, path):
        return obj.int_value, obj.float_value


IntFloatPair = IntFloatPairAdapter(
    Struct(
        "int_marker" / Byte,
        "int_value" / Int,
        "float_marker" / Byte,
        "float_value" / Single,
    )
)


class IntDoublePairAdapter(Adapter):
    def _encode(self, obj, context, path):
        int_value, double_value = obj
        return {
            "int_marker": 0x08,
            "int_value": int_value,
            "double_marker": 0x0D,
            "double_value": double_value,
        }

    def _decode(self, obj, context, path):
        return obj.int_value, obj.double_value


IntDoublePair = IntDoublePairAdapter(
    Struct(
        "int_marker" / Byte,
        "int_value" / Int,
        "double_marker" / Byte,
        "double_value" / Double,
    )
)

TimingPoint = Struct(
    "BPM" / Double,
    "offset" / Double,
    "inherited" / Boolean,
)

if __name__ == "__main__":
    original_string = "Hello, World!"
    data = String.build(original_string)
    result = String.parse(data)
    print(result)

    int_float_data = IntFloatPair.build((123, 4.5))
    int_float_result = IntFloatPair.parse(int_float_data)
    print(int_float_result)

    int_double_data = IntDoublePair.build((123, 4.5))
    int_double_result = IntDoublePair.parse(int_double_data)
    print(int_double_result)
