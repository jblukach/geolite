# IP Intelligence Enrichment with GeoLite2 Databases

## Overview

The **GeoLite2** databases (by **MaxMind**) provides a framework for **IP enrichment and intelligence**.  

- **GeoLite2-City.mmdb**: Adds *geographic context* — where an IP is located.  
- **GeoLite2-ASN.mmdb**: Adds *organizational context* — who owns or operates the IP range.   

Combining these sources delivers a **two-dimensional understanding** of IP data: **geographical** and **organizational**, supporting use cases in **cybersecurity**, **fraud detection**, **analytics**, and **network engineering**.

---

## 1. GeoLite2-City.mmdb

### Purpose
Maps an IP address to its **geographic attributes** down to the **city** level.

### Field Descriptions

| **Field** | **Description** | **Use** |
|------------|------------------|---------|
| **country** | Country name associated with the IP. | Regional reporting, policy enforcement. |
| **c_iso** | ISO 3166-1 alpha-2 country code. | Standardized international reference. |
| **state** | State or region name. | Regional segmentation or service routing. |
| **s_iso** | ISO 3166-2 code for the state. | Consistent data integration. |
| **city** | City associated with the IP. | Targeted analytics, fraud prevention. |
| **zip** | Postal code. | Demographic or proximity analysis. |
| **latitude** | Approximate latitude. | Mapping and distance calculations. |
| **longitude** | Approximate longitude. | Geospatial visualization. |
| **cidr** | CIDR block covering the IP. | Network grouping and lookup efficiency. |

---

## 2. GeoLite2-ASN.mmdb

### Purpose
Maps IP addresses to **Autonomous System Numbers (ASNs)** and network operators.

### Field Descriptions

| **Field** | **Description** | **Use** |
|------------|------------------|---------|
| **asn** | Unique identifier for the network (Autonomous System Number). | ISP or organization attribution. |
| **org** | Organization operating the ASN. | Ownership and routing analysis. |
| **net** | CIDR block of the ASN’s network. | Defines network boundaries for correlation. |

---

## 3. Integrated IP Intelligence Workflow

| **Data Source** | **Question Answered** | **Example Insight** |
|------------------|------------------------|----------------------|
| **GeoLite2-City** | *Where is the IP located?* | Fargo, North Dakota, United States |
| **GeoLite2-ASN** | *Who owns the network?* | ASN 19530 — NDIN-STATE |

### Common Applications
- **Cybersecurity:** Identify malicious or anomalous public IPs by ASN and location.  
- **Fraud Detection:** Correlate user activity with IP ownership and geolocation.  
- **Network Engineering:** Understand IP scope and routing properties.  
- **Analytics:** Combine region and ownership data for insight segmentation.  

---

## 4. How to Use

### Lookup Process
1. **Input** an IP address (e.g., `134.129.111.111`).  
2. **Query** GeoLite2 databases for **City** and **ASN** data.   
3. **Combine** all enrichment results into a unified record.

You can test this process online at:  
🔗 **[https://api.lukach.io/geo/geolite2?134.129.111.111](https://api.lukach.io/geo/geolite2?134.129.111.111)**

### Sample Output
```json
{
    "ip": "134.129.111.111",
    "geo": {
        "country": "United States",
        "c_iso": "US",
        "state": "North Dakota",
        "s_iso": "ND",
        "city": "Fargo",
        "zip": "58102",
        "latitude": 46.9182,
        "longitude": -96.8313,
        "cidr": "134.129.96.0/19"
    },
    "asn": {
        "id": 19530,
        "org": "NDIN-STATE",
        "net": "134.129.0.0/16"
    },
    "attribution": "This product includes GeoLite2 data created by MaxMind, available from https://www.maxmind.com.",
    "geolite2-asn.mmdb": "Thu, 16 Oct 2025 08:30:04 GMT",
    "geolite2-city.mmdb": "Tue, 14 Oct 2025 14:46:21 GMT",
    "region": "us-east-1"
}
```

This unified enrichment result provides **location** and **ownership** in one structured record.

---

## 6. References

- **MaxMind GeoLite2 Developer Documentation**  
  🔗 [https://dev.maxmind.com/geoip/geolite2-free-geolocation-data](https://dev.maxmind.com/geoip/geolite2-free-geolocation-data)

---

## Conclusion

The integration of **GeoLite2-City** and **GeoLite2-ASN** module creates a comprehensive, layered understanding of IP data:

| **Layer** | **Source** | **Insight** |
|------------|-------------|-------------|
| **Geographical** | GeoLite2-City | Where the IP is located |
| **Organizational** | GeoLite2-ASN | Who owns or operates the IP |

Together, these tools provide the foundation for a powerful **IP enrichment pipeline**, enabling accurate, two-dimensional insights across **security**, **analytics**, and **infrastructure monitoring**.
