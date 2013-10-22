# Copyright (c) 2003-2006 CORE Security Technologies
#
# This software is provided under under a slightly modified version
# of the Apache Software License. See the accompanying LICENSE file
# for more information.
#
# $Id$
#
# Description:
#  Convenience packet unpackers for various network protocols
#  implemented in the ImpactPacket module.
#
# Author:
#  Javier Burroni (javier)
#  Bruce Leidl (brl)

import ImpactPacket
import dot11

"""Classes to convert from raw packets into a hierarchy of
ImpactPacket derived objects.

The protocol of the outermost layer must be known in advance, and the
packet must be fed to the corresponding decoder. From there it will
try to decode the raw data into a hierarchy of ImpactPacket derived
objects; if a layer's protocol is unknown, all the remaining data will
be wrapped into a ImpactPacket.Data object.
"""

class Decoder:
    __decoded_protocol = None
    def decode(self, aBuffer):
        pass
        
    def set_decoded_protocol(self, protocol):
        self.__decoded_protocol = protocol
        
    def get_protocol(self, aprotocol):
        protocol = self.__decoded_protocol
        while protocol:
            if protocol.__class__ == aprotocol:
                break
            protocol=protocol.child()
        return protocol

class EthDecoder(Decoder):
    def __init__(self):
        pass

    def decode(self, aBuffer):
        e = ImpactPacket.Ethernet(aBuffer)
        self.set_decoded_protocol( e )
        off = e.get_header_size()
        if e.get_ether_type() == ImpactPacket.IP.ethertype:
            self.ip_decoder = IPDecoder()
            packet = self.ip_decoder.decode(aBuffer[off:])
        elif e.get_ether_type() == ImpactPacket.ARP.ethertype:
            self.arp_decoder = ARPDecoder()
            packet = self.arp_decoder.decode(aBuffer[off:])
        else:
            self.data_decoder = DataDecoder()
            packet = self.data_decoder.decode(aBuffer[off:])

        e.contains(packet)
        return e

# Linux "cooked" capture encapsulation.
# Used, for instance, for packets returned by the "any" interface.
class LinuxSLLDecoder(Decoder):
    def __init__(self):
        pass

    def decode(self, aBuffer):
        e = ImpactPacket.LinuxSLL(aBuffer)
        self.set_decoded_protocol( e )
        off = 16
        if e.get_ether_type() == ImpactPacket.IP.ethertype:
            self.ip_decoder = IPDecoder()
            packet = self.ip_decoder.decode(aBuffer[off:])
        elif e.get_ether_type() == ImpactPacket.ARP.ethertype:
            self.arp_decoder = ARPDecoder()
            packet = self.arp_decoder.decode(aBuffer[off:])
        else:
            self.data_decoder = DataDecoder()
            packet = self.data_decoder.decode(aBuffer[off:])

        e.contains(packet)
        return e

class IPDecoder(Decoder):
    def __init__(self):
        pass

    def decode(self, aBuffer):
        i = ImpactPacket.IP(aBuffer)
        self.set_decoded_protocol ( i )
        off = i.get_header_size()
        end = i.get_ip_len()
        if i.get_ip_p() == ImpactPacket.UDP.protocol:
            self.udp_decoder = UDPDecoder()
            packet = self.udp_decoder.decode(aBuffer[off:end])
        elif i.get_ip_p() == ImpactPacket.TCP.protocol:
            self.tcp_decoder = TCPDecoder()
            packet = self.tcp_decoder.decode(aBuffer[off:end])
        elif i.get_ip_p() == ImpactPacket.ICMP.protocol:
            self.icmp_decoder = ICMPDecoder()
            packet = self.icmp_decoder.decode(aBuffer[off:end])
        else:
            self.data_decoder = DataDecoder()
            packet = self.data_decoder.decode(aBuffer[off:end])
        i.contains(packet)
        return i

class ARPDecoder(Decoder):
    def __init__(self):
        pass

    def decode(self, aBuffer):
        arp = ImpactPacket.ARP(aBuffer)
        self.set_decoded_protocol( arp )
        off = arp.get_header_size()
        self.data_decoder = DataDecoder()
        packet = self.data_decoder.decode(aBuffer[off:])
        arp.contains(packet)
        return arp

class UDPDecoder(Decoder):
    def __init__(self):
        pass

    def decode(self, aBuffer):
        u = ImpactPacket.UDP(aBuffer)
        self.set_decoded_protocol( u )
        off = u.get_header_size()
        self.data_decoder = DataDecoder()
        packet = self.data_decoder.decode(aBuffer[off:])
        u.contains(packet)
        return u

class TCPDecoder(Decoder):
    def __init__(self):
        pass

    def decode(self, aBuffer):
        t = ImpactPacket.TCP(aBuffer)
        self.set_decoded_protocol( t )
        off = t.get_header_size()
        self.data_decoder = DataDecoder()
        packet = self.data_decoder.decode(aBuffer[off:])
        t.contains(packet)
        return t

class IPDecoderForICMP(Decoder):
    """This class was added to parse the IP header of ICMP unreachables packets
    If you use the "standard" IPDecoder, it might crash (see bug #4870) ImpactPacket.py
    because the TCP header inside the IP header is incomplete"""    
    def __init__(self):
        pass

    def decode(self, aBuffer):
        i = ImpactPacket.IP(aBuffer)
        self.set_decoded_protocol( i )
        off = i.get_header_size()
        if i.get_ip_p() == ImpactPacket.UDP.protocol:
            self.udp_decoder = UDPDecoder()
            packet = self.udp_decoder.decode(aBuffer[off:])
        else:
            self.data_decoder = DataDecoder()
            packet = self.data_decoder.decode(aBuffer[off:])
        i.contains(packet)
        return i

class ICMPDecoder(Decoder):
    def __init__(self):
        pass

    def decode(self, aBuffer):
        ic = ImpactPacket.ICMP(aBuffer)
        self.set_decoded_protocol( ic )
        off = ic.get_header_size()
        if ic.get_icmp_type() == ImpactPacket.ICMP.ICMP_UNREACH:
            self.ip_decoder = IPDecoderForICMP()
            packet = self.ip_decoder.decode(aBuffer[off:])
        else:
            self.data_decoder = DataDecoder()
            packet = self.data_decoder.decode(aBuffer[off:])
        ic.contains(packet)
        return ic

class DataDecoder(Decoder):
    def decode(self, aBuffer):
        d = ImpactPacket.Data(aBuffer)
        self.set_decoded_protocol( d )
        return d

class RadioTapDecoder(Decoder):
    def __init__(self):
        pass

    def decode(self, aBuffer):
        rt = dot11.RadioTap(aBuffer)
        self.set_decoded_protocol( rt )
        
        self.do11_decoder = Dot11Decoder()
        flags=rt.get_flags()
        if flags is not None:
            fcs=flags&dot11.RadioTap.RTF_FLAGS.PROPERTY_FCS_AT_END
            self.do11_decoder.FCS_at_end(fcs)
            
        packet = self.do11_decoder.decode(rt.get_body_as_string())
    
        rt.contains(packet)
        return rt

class Dot11Decoder(Decoder):
    __FCS_at_end = True
    def __init__(self):
        pass
        
    def FCS_at_end(self, fcs_at_end=True):
        self.__FCS_at_end=not not fcs_at_end 
        
    def decode(self, aBuffer):
        d = dot11.Dot11(aBuffer, self.__FCS_at_end)
        self.set_decoded_protocol( d )
        
        type = d.get_type()
        if type == dot11.Dot11Types.DOT11_TYPE_CONTROL:
            dot11_control_decoder = Dot11ControlDecoder()
            packet = dot11_control_decoder.decode(d.body_string)
        elif type == dot11.Dot11Types.DOT11_TYPE_DATA:
            dot11_data_decoder = Dot11DataDecoder()
            if d.get_fromDS() and d.get_toDS():
                dot11_data_decoder.set_Addr4()
            if d.is_QoS_frame():
                dot11_data_decoder.set_QoS()
            if d.get_protectedFrame():
                dot11_data_decoder.set_privateFrame()
                
            packet = dot11_data_decoder.decode(d.body_string)
        elif type == dot11.Dot11Types.DOT11_TYPE_MANAGEMENT:
            dot11_management_decoder = Dot11ManagementDecoder()
            dot11_management_decoder.set_subtype(d.get_subtype())
            packet = dot11_management_decoder.decode(d.body_string)
        else:
            data_decoder = DataDecoder()
            packet = data_decoder.decode(d.body_string)

        d.contains(packet)
        return d

class Dot11ControlDecoder(Decoder):
    __FCS_at_end = True
    def __init__(self):
        pass

    def FCS_at_end(self, fcs_at_end=True):
        self.__FCS_at_end=not not fcs_at_end 
    
    def decode(self, aBuffer):
        d = dot11.Dot11(aBuffer, self.__FCS_at_end)
        self.set_decoded_protocol(d)
        
        self.subtype = d.get_subtype()
        if self.subtype is dot11.Dot11Types.DOT11_SUBTYPE_CONTROL_CLEAR_TO_SEND:
            self.ctrl_cts_decoder = Dot11ControlFrameCTSDecoder()
            packet = self.ctrl_cts_decoder.decode(d.body_string)
        elif self.subtype is dot11.Dot11Types.DOT11_SUBTYPE_CONTROL_ACKNOWLEDGMENT:
            self.ctrl_ack_decoder = Dot11ControlFrameACKDecoder()
            packet = self.ctrl_ack_decoder.decode(d.body_string)
        elif self.subtype is dot11.Dot11Types.DOT11_SUBTYPE_CONTROL_REQUEST_TO_SEND:
            self.ctrl_rts_decoder = Dot11ControlFrameRTSDecoder()
            packet = self.ctrl_rts_decoder.decode(d.body_string)
        elif self.subtype is dot11.Dot11Types.DOT11_SUBTYPE_CONTROL_POWERSAVE_POLL:
            self.ctrl_pspoll_decoder = Dot11ControlFramePSPollDecoder()
            packet = self.ctrl_pspoll_decoder.decode(d.body_string)
        elif self.subtype is dot11.Dot11Types.DOT11_SUBTYPE_CONTROL_CF_END:
            self.ctrl_cfend_decoder = Dot11ControlFrameCFEndDecoder()
            packet = self.ctrl_cfend_decoder.decode(d.body_string)
        elif self.subtype is dot11.Dot11Types.DOT11_SUBTYPE_CONTROL_CF_END_CF_ACK:
            self.ctrl_cfendcfack_decoder = Dot11ControlFrameCFEndCFACKDecoder()
            packet = self.ctrl_cfendcfack_decoder.decode(d.body_string)
        else:
            data_decoder = DataDecoder()
            packet = data_decoder.decode(d.body_string)
        
        d.contains(packet)
        return d

class Dot11ControlFrameCTSDecoder(Decoder):
    def __init__(self):
        pass
    
    def decode(self, aBuffer):
        p = dot11.Dot11ControlFrameCTS(aBuffer)
        self.set_decoded_protocol(p)
        return p

class Dot11ControlFrameACKDecoder(Decoder):
    def __init__(self):
        pass
    
    def decode(self, aBuffer):
        p = dot11.Dot11ControlFrameACK(aBuffer)
        self.set_decoded_protocol(p)
        return p

class Dot11ControlFrameRTSDecoder(Decoder):
    def __init__(self):
        pass
    
    def decode(self, aBuffer):
        p = dot11.Dot11ControlFrameRTS(aBuffer)
        self.set_decoded_protocol(p)
        return p

class Dot11ControlFramePSPollDecoder(Decoder):
    def __init__(self):
        pass
    
    def decode(self, aBuffer):
        p = dot11.Dot11ControlFramePSPoll(aBuffer)
        self.set_decoded_protocol(p)
        return p

class Dot11ControlFrameCFEndDecoder(Decoder):
    def __init__(self):
        pass
    
    def decode(self, aBuffer):
        p = dot11.Dot11ControlFrameCFEnd(aBuffer)
        self.set_decoded_protocol(p)
        return p

class Dot11ControlFrameCFEndCFACKDecoder(Decoder):
    def __init__(self):
        pass
    
    def decode(self, aBuffer):
        p = dot11.Dot11ControlFrameCFEndCFACK(aBuffer)
        self.set_decoded_protocol(p)
        return p

class Dot11DataDecoder(Decoder):
    def __init__(self):
        self.QoS=False
        self.Addr4=False
        self.Private=False
        
    def set_QoS(self):
        self.QoS = True
    def set_Addr4(self):
        self.Addr4 = True
    def set_privateFrame(self):
        self.Private = True
        
    def decode(self, aBuffer):
        if self.Addr4:
            if self.QoS:
                p = dot11.Dot11DataAddr4QoSFrame(aBuffer)
            else:
                p = dot11.Dot11DataAddr4Frame(aBuffer)
        elif self.QoS:
            p = dot11.Dot11DataQoSFrame(aBuffer)
        else:
            p = dot11.Dot11DataFrame(aBuffer)
        self.set_decoded_protocol( p )
        
        if self.Private is False:
            self.llc_decoder = LLCDecoder()
            packet = self.llc_decoder.decode(p.body_string)
        else:
            wep_decoder = Dot11WEPDecoder()
            packet = wep_decoder.decode(p.body_string)
            if packet is None:
                wpa_decoder = Dot11WPADecoder()
                packet = wpa_decoder.decode(p.body_string)
                if packet is None:
                    wpa2_decoder = Dot11WPA2Decoder()
                    packet = wpa2_decoder.decode(p.body_string)
                    if packet is None:
                        data_decoder = DataDecoder()
                        packet = data_decoder.decode(p.body_string)
        
        p.contains(packet)
        return p
      
class Dot11WEPDecoder(Decoder):
    def __init__(self):
        pass
        
    def decode(self, aBuffer, key=None):
        wep = dot11.Dot11WEP(aBuffer)
        self.set_decoded_protocol( wep )

        if wep.is_WEP() is False:
            return None
        
    if key:
            decoded_string=wep.decrypt_data()
            
            wep_data = Dot11WEPDataDecoder()
            packet = wep_data.decode(decoded_string)
    else:
        data_decoder = DataDecoder()
        packet = data_decoder.decode(wep.body_string)

        wep.contains(packet)
        
        return wep

    def decrypt_data(self, key_string):
        'Return \'WEP Data\' decrypted'
        
        # Needs to be at least 8 bytes of payload 
        if len(self.body_string)<8:
            return self.body_string
        
        # initialize the first bytes of the key from the IV 
        # and copy rest of the WEP key (the secret part) 
        key=self.get_iv()+key_string
        keylen=3+len(key_string) # add in IV bytes

        # set up the RC4 state
        j = 0
        s = range(256)
        for i in range(256):
            j = (j + s[i] + ord(key[i % len(key)])) & 0xff
            s[i],s[j] = s[j],s[i] # SSWAP(i,j)
            
        # Apply the RC4 to the data, update the CRC32
        out = ""
        i = j = 0
        for c in data:
            i = (i+1) & 0xff
            j = (j+s[i]) & 0xff
            s[i],s[j] = s[j],s[i] # SSWAP(i,j)
            d=chr(ord(c) ^ s[(s[i] + s[j]) & 0xff])
            out+=d
        dwd=Dot11WEPData(out)
        
        if False: # is ICV correct
            return dwd
        else:
            return self.body_string


class Dot11WEPDataDecoder(Decoder):
    def __init__(self):
        pass
        
    def decode(self, aBuffer):
        wep_data = dot11.Dot11WEPData(aBuffer)
        self.set_decoded_protocol( wep_data )

        llc_decoder = LLCDecoder()
        packet = llc_decoder.decode(wep_data.body_string)
        
        wep_data.contains(packet)
        
        return wep_data


class Dot11WPADecoder(Decoder):
    def __init__(self):
        pass
        
    def decode(self, aBuffer, key=None):
        wpa = dot11.Dot11WPA(aBuffer)
        self.set_decoded_protocol( wpa )

        if wpa.is_WPA() is False:
            return None
        
	if key:
		decoded_string=wpa.get_decrypted_data()
		
		wpa_data = Dot11DataWPADataDecoder()
		packet = wpa_data.decode(decoded_string)
	else:
		data_decoder = DataDecoder()
		packet = data_decoder.decode(wpa.body_string)
        
        wpa.contains(packet)
        
        return wpa
    
class Dot11WPADataDecoder(Decoder):
    def __init__(self):
        pass
        
    def decode(self, aBuffer):
        wpa_data = dot11.Dot11WPAData(aBuffer)
        self.set_decoded_protocol( wpa_data )

        llc_decoder = LLCDecoder()
        packet = self.llc_decoder.decode(wpa_data.body_string)
        
        wpa_data.contains(packet)
        
        return wpa_data

class Dot11WPA2Decoder(Decoder):
    def __init__(self):
        pass
        
    def decode(self, aBuffer, key=None):
        wpa2 = dot11.Dot11WPA2(aBuffer)
        self.set_decoded_protocol( wpa2 )

        if wpa2.is_WPA2() is False:
            return None
        
	if key:
		decoded_string=wpa2.get_decrypted_data()
		
		wpa2_data = Dot11WPA2DataDecoder()
		packet = wpa2_data.decode(decoded_string)
	else:
		data_decoder = DataDecoder()
		packet = data_decoder.decode(wpa2.body_string)
        
        wpa2.contains(packet)
        
        return wpa2
    
class Dot11WPA2DataDecoder(Decoder):
    def __init__(self):
        pass
        
    def decode(self, aBuffer):
        wpa2_data = dot11.Dot11WPA2Data(aBuffer)
        self.set_decoded_protocol( wpa2_data )

        llc_decoder = LLCDecoder()
        packet = self.llc_decoder.decode(wpa2_data.body_string)
        
        wpa2_data.contains(packet)
        
        return wpa2_data
    
class LLCDecoder(Decoder):
    def __init__(self):
        pass
        
    def decode(self, aBuffer):
        d = dot11.LLC(aBuffer)
        self.set_decoded_protocol( d )
        
        if d.get_DSAP()==dot11.SAPTypes.SNAP:
            if d.get_SSAP()==dot11.SAPTypes.SNAP:
                if d.get_control()==dot11.LLC.DLC_UNNUMBERED_FRAMES:
                    snap_decoder = SNAPDecoder()
                    packet = snap_decoder.decode(d.body_string)
        else:
            # Only SNAP is implemented
            data_decoder = DataDecoder()
            packet = data_decoder.decode(d.body_string)

        d.contains(packet)
        return d

class SNAPDecoder(Decoder):
    def __init__(self):
        pass
        
    def decode(self, aBuffer):
        s = dot11.SNAP(aBuffer)
        self.set_decoded_protocol( s )
        
        if  s.get_OUI()!=0x000000:
            # We don't know how to handle other than OUI=0x000000 (EtherType)
            self.data_decoder = DataDecoder()
            packet = self.data_decoder.decode(s.body_string)
        elif s.get_protoID() == ImpactPacket.IP.ethertype:
            self.ip_decoder = IPDecoder()
            packet = self.ip_decoder.decode(s.body_string)
        elif s.get_protoID() == ImpactPacket.ARP.ethertype:
            self.arp_decoder = ARPDecoder()
            packet = self.arp_decoder.decode(s.body_string)
        else:
            self.data_decoder = DataDecoder()
            packet = self.data_decoder.decode(s.body_string)

        s.contains(packet)
        return s

class Dot11ManagementDecoder(Decoder):
    subtype = None
    def __init__(self):
        pass
        
    def set_subtype(self, subtype):
        self.subtype=subtype
    
    def decode(self, aBuffer):
        p = dot11.Dot11ManagementFrame(aBuffer)
        self.set_decoded_protocol( p )
        
        if self.subtype is dot11.Dot11Types.DOT11_SUBTYPE_MANAGEMENT_BEACON:
            self.mgt_beacon_decoder = Dot11ManagementBeaconDecoder()
            packet = self.mgt_beacon_decoder.decode(p.body_string)
        elif self.subtype is dot11.Dot11Types.DOT11_SUBTYPE_MANAGEMENT_PROBE_REQUEST:
            self.mgt_probe_request_decoder = Dot11ManagementProbeRequestDecoder()
            packet = self.mgt_probe_request_decoder.decode(p.body_string)
        elif self.subtype is dot11.Dot11Types.DOT11_SUBTYPE_MANAGEMENT_PROBE_RESPONSE:
            self.mgt_probe_response_decoder = Dot11ManagementProbeResponseDecoder()
            packet = self.mgt_probe_response_decoder.decode(p.body_string)				
        else:
            data_decoder = DataDecoder()
            packet = data_decoder.decode(p.body_string)
        
        p.contains(packet)
        return p

class Dot11ManagementBeaconDecoder(Decoder):
    def __init__(self):
        pass
        
    def decode(self, aBuffer):
        p = dot11.Dot11ManagementBeacon(aBuffer)
        self.set_decoded_protocol( p )
        
        return p

class Dot11ManagementProbeRequestDecoder(Decoder):
    def __init__(self):
        pass
        
    def decode(self, aBuffer):
        p = dot11.Dot11ManagementProbeRequest(aBuffer)
        self.set_decoded_protocol( p )
        
        return p

class Dot11ManagementProbeResponseDecoder(Decoder):
    def __init__(self):
        pass
        
    def decode(self, aBuffer):
        p = dot11.Dot11ManagementProbeResponse(aBuffer)
        self.set_decoded_protocol( p )
        
        return p