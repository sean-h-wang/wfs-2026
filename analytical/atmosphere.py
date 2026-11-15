import math

def standard_atmosphere(Z: float):
    """
    Get atmospheric properties at altitude Z (in METERS) using the 1976 Standard Atmosphere model.
    Args:
        Z: Geometric altitude in METERS (limited to 80 km)
    Returns:
        T_inf: Freestream temperature in Kelvin
        P_inf: Freestream Pressure in Pascals
        rho_inf: Freestream Air density in kg/m³
    """

    if Z < 0 or Z > 80000:
        raise ValueError("Altitude Z must be between 0 and 80,000 meters.")
    
    # Constants
    g0 = 9.80665       # Standard gravity [m/s²]
    R_gas = 287.052874 # Specific gas constant for air [J/(kg·K)]

    r_e = 6356766.0  # Earth radius in meters
    H = r_e*Z / (r_e + Z)  # Geopotential altitude in meters

    lapse_rates = [-0.0065, 0.0, 0.001, 0.0028, 0.0, -0.0028, -0.002]  # K/m'
    geopotential_heights = [0, 11000, 20000, 32000, 47000, 51000, 71000, 84852]  # m'
    
    T_base = [288.15] # base temperatures for each layer (later base temperatures are calculated iteratively)
    P_base = [101325.0] # base pressures for each layer (later base pressures are calculated iteratively)

    # Calculate base temperatures.
    for i in range(1, len(geopotential_heights)):
        L = lapse_rates[i-1]
        H_lower = geopotential_heights[i-1]
        T_lower = T_base[i-1]
        T_base.append(T_lower + L * (geopotential_heights[i] - H_lower))

    # Calculate base pressures.
    for i in range(1, len(geopotential_heights)):
        temperature_lapse_rate = lapse_rates[i-1]
        H_lower = geopotential_heights[i-1]
        T_lower = T_base[i-1]
        P_lower = P_base[i-1]
        
        if temperature_lapse_rate == 0:
            exponent = -g0 / (R_gas * T_lower) * (geopotential_heights[i] - H_lower)
            P_base.append(P_lower * math.exp(exponent))
        else: 
            P_base.append(P_lower * (T_lower / T_base[i])**(g0 / (R_gas * temperature_lapse_rate)))

    
    # Calculate User Altitude Properties
    for i in range(0, len(geopotential_heights) - 1):
        if H >= geopotential_heights[i] and H < geopotential_heights[i + 1]:
            # subscript i of interest.
            
            temperature_lapse_rate = lapse_rates[i]
            H_lower = geopotential_heights[i]
            T_lower = T_base[i]
            P_lower = P_base[i]
            
            T_inf = T_lower + temperature_lapse_rate * (H - H_lower)
            if temperature_lapse_rate == 0:
                P_inf = P_lower * math.exp(-g0 / (R_gas * T_lower) * (H - H_lower))
            else:
                P_inf = P_lower * (T_lower / T_inf) ** (g0 / (R_gas * temperature_lapse_rate))
            break
    
    # Calculate rho_inf:
    rho_inf = P_inf / (R_gas * T_inf)

    return T_inf, P_inf, rho_inf