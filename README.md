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
| **country** | Country name followed by its ISO code when available. | Regional reporting, policy enforcement. |
| **state** | State or region name. | Regional segmentation or service routing. |
| **city** | City associated with the IP. | Targeted analytics, fraud prevention. |
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
2. **Query** the local `GeoLite2-ASN.mmdb` and `GeoLite2-City.mmdb` files.
3. **Combine** the ASN and geographic data into a unified result record.

The handler accepts `ip`, `ipAddress`, `query`, or `ips` values through query
parameters, JSON bodies, or API Gateway path parameters. Multiple values are
returned in input order under `results`; invalid values receive an entry-level
`error`.

You can test this process online at:  
[https://api.lukach.io/geo?ip=134.129.111.111](https://api.lukach.io/geo?ip=134.129.111.111)

### Sample Output
```json
{
    "results": [
        {
            "ip": "134.129.111.111",
            "geo": {
                "country": "United States - US",
                "state": "North Dakota",
                "city": "Fargo",
                "cidr": "134.129.96.0/19"
            },
            "asn": {
                "id": 19530,
                "org": "NDIN-STATE",
                "net": "134.129.0.0/16"
            }
        }
    ],
    "requested_count": 1,
    "attribution": "This product includes GeoLite2 data created by MaxMind, available from https://www.maxmind.com.",
    "geolite2-asn.mmdb": "2025-10-16T08:30:04Z",
    "geolite2-city.mmdb": "2025-10-14T14:46:21Z",
    "timestamp_utc": "2026-08-05T00:00:00Z",
    "region": "us-east-1"
}
```

This unified enrichment result provides **location** and **ownership** in one structured record.

---

## 5. References

- **MaxMind GeoLite2 Developer Documentation**  
    [https://dev.maxmind.com/geoip/geolite2-free-geolocation-data](https://dev.maxmind.com/geoip/geolite2-free-geolocation-data)

---

## Conclusion

The integration of **GeoLite2-City** and **GeoLite2-ASN** module creates a comprehensive, layered understanding of IP data:

| **Layer** | **Source** | **Insight** |
|------------|-------------|-------------|
| **Geographical** | GeoLite2-City | Where the IP is located |
| **Organizational** | GeoLite2-ASN | Who owns or operates the IP |

Together, these tools provide the foundation for a powerful **IP enrichment pipeline**, enabling accurate, two-dimensional insights across **security**, **analytics**, and **infrastructure monitoring**.

