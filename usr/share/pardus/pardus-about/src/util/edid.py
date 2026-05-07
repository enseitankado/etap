import struct


class Edid:
    def __init__(self, data: bytes):
        if len(data) < 128:
            raise ValueError("EDID data must be at least 128 bytes")

        self._raw = data[:128]

        self.manufacturer = ""
        self.model_id = 0
        self.serial_number = 0
        self.manufacture_week = 0
        self.manufacture_year = 0
        self.edid_version = ""
        self.revision = ""
        self.video_input_definition = {}
        self.max_horizontal_image_size_cm = 0
        self.max_vertical_image_size_cm = 0
        self.display_gamma = 0.0
        self.dpms_features = {}
        self.chromaticity = {}
        self.established_timings = []
        self.standard_timings = []
        self.name = ""
        self.serial_text = ""
        self.resolution_width = 0
        self.resolution_height = 0
        self.refresh_rate = 0.0
        self.extension_flag = 0
        self.checksum = 0

        self._parse()

    def _parse(self):
        if self._raw[0:8] != b"\x00\xff\xff\xff\xff\xff\xff\x00":
            raise ValueError("Invalid EDID Header")

        self._parse_vendor_product()
        self._parse_edid_structure()
        self._parse_display_parameters()
        self._parse_chromaticity()
        self._parse_established_timings()
        self._parse_standard_timings()
        self._parse_descriptors()

        self.extension_flag = self._raw[126]
        self.checksum = self._raw[127]

    def _parse_vendor_product(self):
        mfg_raw = struct.unpack(">H", self._raw[8:10])[0]
        self.manufacturer = "".join(
            [
                chr(((mfg_raw >> 10) & 0x1F) + 64),
                chr(((mfg_raw >> 5) & 0x1F) + 64),
                chr((mfg_raw & 0x1F) + 64),
            ]
        )
        self.model_id = struct.unpack("<H", self._raw[10:12])[0]
        self.serial_number = struct.unpack("<I", self._raw[12:16])[0]
        self.manufacture_week = self._raw[16]
        self.manufacture_year = self._raw[17] + 1990

    def _parse_edid_structure(self):
        self.edid_version = str(self._raw[18])
        self.revision = str(self._raw[19])

    def _parse_display_parameters(self):
        byte_20 = self._raw[20]
        if byte_20 & 0x80:
            self.video_input_definition = {
                "type": "Digital",
                "dfp_1_x_compatible": bool(byte_20 & 0x01),
            }
        else:
            self.video_input_definition = {
                "type": "Analog",
                "voltage_level": (byte_20 & 0x60) >> 5,
                "sync_separate": bool(byte_20 & 0x08),
                "sync_composite": bool(byte_20 & 0x04),
                "sync_green": bool(byte_20 & 0x02),
                "serration_vsync": bool(byte_20 & 0x01),
            }

        self.max_horizontal_image_size_cm = self._raw[21]
        self.max_vertical_image_size_cm = self._raw[22]

        gamma_raw = self._raw[23]
        if gamma_raw == 0xFF:
            self.display_gamma = 0.0
        else:
            self.display_gamma = (gamma_raw + 100) / 100.0

        byte_24 = self._raw[24]
        self.dpms_features = {
            "standby": bool(byte_24 & 0x80),
            "suspend": bool(byte_24 & 0x40),
            "active_off": bool(byte_24 & 0x20),
            "display_type": (byte_24 & 0x18) >> 3,
            "srgb_is_standard": bool(byte_24 & 0x04),
            "preferred_timing_mode": bool(byte_24 & 0x02),
            "gtf_supported": bool(byte_24 & 0x01),
        }

    def _parse_chromaticity(self):
        rx_low = (self._raw[25] >> 6) & 0x03
        ry_low = (self._raw[25] >> 4) & 0x03
        gx_low = (self._raw[25] >> 2) & 0x03
        gy_low = (self._raw[25] >> 0) & 0x03
        bx_low = (self._raw[26] >> 6) & 0x03
        by_low = (self._raw[26] >> 4) & 0x03
        wx_low = (self._raw[26] >> 2) & 0x03
        wy_low = (self._raw[26] >> 0) & 0x03

        rx = (self._raw[27] << 2) | rx_low
        ry = (self._raw[28] << 2) | ry_low
        gx = (self._raw[29] << 2) | gx_low
        gy = (self._raw[30] << 2) | gy_low
        bx = (self._raw[31] << 2) | bx_low
        by = (self._raw[32] << 2) | by_low
        wx = (self._raw[33] << 2) | wx_low
        wy = (self._raw[34] << 2) | wy_low

        self.chromaticity = {
            "red_x": rx / 1024.0,
            "red_y": ry / 1024.0,
            "green_x": gx / 1024.0,
            "green_y": gy / 1024.0,
            "blue_x": bx / 1024.0,
            "blue_y": by / 1024.0,
            "white_x": wx / 1024.0,
            "white_y": wy / 1024.0,
        }

    def _parse_established_timings(self):
        b1 = self._raw[35]
        b2 = self._raw[36]
        b3 = self._raw[37]

        timings = []
        if b1 & 0x80:
            timings.append("720x400 @ 70Hz")
        if b1 & 0x40:
            timings.append("720x400 @ 88Hz")
        if b1 & 0x20:
            timings.append("640x480 @ 60Hz")
        if b1 & 0x10:
            timings.append("640x480 @ 67Hz")
        if b1 & 0x08:
            timings.append("640x480 @ 72Hz")
        if b1 & 0x04:
            timings.append("640x480 @ 75Hz")
        if b1 & 0x02:
            timings.append("800x600 @ 56Hz")
        if b1 & 0x01:
            timings.append("800x600 @ 60Hz")

        if b2 & 0x80:
            timings.append("800x600 @ 72Hz")
        if b2 & 0x40:
            timings.append("800x600 @ 75Hz")
        if b2 & 0x20:
            timings.append("832x624 @ 75Hz")
        if b2 & 0x10:
            timings.append("1024x768 @ 87Hz (I)")
        if b2 & 0x08:
            timings.append("1024x768 @ 60Hz")
        if b2 & 0x04:
            timings.append("1024x768 @ 70Hz")
        if b2 & 0x02:
            timings.append("1024x768 @ 75Hz")
        if b2 & 0x01:
            timings.append("1280x1024 @ 75Hz")

        if b3 & 0x80:
            timings.append("1152x870 @ 75Hz")

        self.established_timings = timings

    def _parse_standard_timings(self):
        for i in range(38, 54, 2):
            b1 = self._raw[i]
            b2 = self._raw[i + 1]
            if b1 == 0x01 and b2 == 0x01:
                continue

            h_res = (b1 + 31) * 8
            aspect_ratio_bits = (b2 >> 6) & 0x03
            freq = (b2 & 0x3F) + 60

            v_res = 0
            ratio_str = ""

            if aspect_ratio_bits == 0:
                v_res = int(h_res / 1.6) if self._raw[19] < 3 else int(h_res * 10 / 16)
                ratio_str = "16:10"
            elif aspect_ratio_bits == 1:
                v_res = int(h_res * 3 / 4)
                ratio_str = "4:3"
            elif aspect_ratio_bits == 2:
                v_res = int(h_res * 4 / 5)
                ratio_str = "5:4"
            elif aspect_ratio_bits == 3:
                v_res = int(h_res * 9 / 16)
                ratio_str = "16:9"

            self.standard_timings.append(
                {"width": h_res, "height": v_res, "frequency": freq, "ratio": ratio_str}
            )

    def _parse_descriptors(self):
        descriptor_offsets = [54, 72, 90, 108]

        preferred_timing_block = self._raw[54:72]
        if preferred_timing_block[0] != 0 or preferred_timing_block[1] != 0:
            h_active = preferred_timing_block[2] + (
                (preferred_timing_block[4] & 0xF0) << 4
            )
            v_active = preferred_timing_block[5] + (
                (preferred_timing_block[7] & 0xF0) << 4
            )

            pixel_clock = struct.unpack("<H", preferred_timing_block[0:2])[0] * 10000
            h_total = (
                h_active
                + preferred_timing_block[3]
                + ((preferred_timing_block[4] & 0x0F) << 8)
            )
            v_total = (
                v_active
                + preferred_timing_block[6]
                + ((preferred_timing_block[7] & 0x0F) << 8)
            )

            if h_total > 0 and v_total > 0:
                self.resolution_width = h_active
                self.resolution_height = v_active
                self.refresh_rate = pixel_clock / (h_total * v_total)

        for offset in descriptor_offsets:
            block = self._raw[offset : offset + 18]
            if block[0] == 0 and block[1] == 0:
                tag = block[3]
                data_chunk = block[5:]
                if tag == 0xFC:
                    self.name = self._clean_string(data_chunk)
                elif tag == 0xFF:
                    self.serial_text = self._clean_string(data_chunk)

    def _clean_string(self, byte_data):
        text = byte_data.split(b"\x0a")[0]
        return text.decode("cp437", errors="ignore").strip()

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}
