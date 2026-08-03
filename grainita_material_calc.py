import math
# Atomic data: Z, A
E = {'H':(1,1.008),'O':(8,15.999),'Na':(11,22.990),'Zn':(30,65.38),'W':(74,183.84)}

def X0_elem(Z,A):
    # Tsai / PDG approximation, g/cm^2
    return 716.4*A/(Z*(Z+1)*math.log(287.0/math.sqrt(Z)))

def Ec(Z):  # critical energy, solids/liquids, MeV
    return 610.0/(Z+1.24)

def compound(formula, name):
    """formula: dict element->count. returns (M, {elem: massfrac})"""
    M = sum(E[e][1]*n for e,n in formula.items())
    w = {e: E[e][1]*n/M for e,n in formula.items()}
    return M, w

def merge(parts):
    """parts: list of (massfrac_of_part, {elem:massfrac_within_part})"""
    out={}
    for f,w in parts:
        for e,x in w.items(): out[e]=out.get(e,0)+f*x
    return out

def props(w, rho):
    invX0 = sum(x/X0_elem(*E[e]) for e,x in w.items())
    X0_mass = 1.0/invX0                      # g/cm^2
    X0_cm   = X0_mass/rho
    # Moliere: 1/Rm = (1/Es) * sum w_j Ec_j / X0_j   with Es=21.2 MeV
    invRm = sum(x*Ec(E[e][0])/X0_elem(*E[e]) for e,x in w.items())/21.2
    Rm_mass = 1.0/invRm
    Zeff = sum(x*E[e][0] for e,x in w.items())/sum(x for e,x in w.items())
    return X0_mass, X0_cm, Rm_mass/rho, Zeff

ZnWO4_M, ZnWO4_w = compound({'Zn':1,'W':1,'O':4},'ZnWO4')
SPT_M,   SPT_w   = compound({'Na':6,'H':2,'W':12,'O':40},'Na6H2W12O40')
H2O_M,   H2O_w   = compound({'H':2,'O':1},'H2O')

print("--- pure ZnWO4 (rho=7.87) ---")
print("X0 = %.4f g/cm2  = %.3f cm ; Rm = %.3f cm ; Zeff=%.1f" % props(ZnWO4_w,7.87))

# heavy liquid: SPT in water tuned to rho_l
for rho_l in (2.8,3.0,3.1):
    rho_spt=4.0
    # ideal volume mixing: 1/rho = w/rho_spt + (1-w)/1.0
    w = (1.0 - 1.0/rho_l)/(1.0 - 1.0/rho_spt)
    liq_w = merge([(w,SPT_w),(1-w,H2O_w)])
    Xm,Xc,Rm,Z = props(liq_w,rho_l)
    print("liquid rho=%.2f  -> %.1f%% SPT by mass ; X0=%.2f g/cm2 = %.2f cm ; Zeff=%.1f"%(rho_l,100*w,Xm,Xc,Z))

print("\n--- GRAiNITA mixture: 80% ZnWO4 / 20% liquid by mass ---")
for rho_l in (2.8,3.0,3.1):
    rho_spt=4.0
    wspt = (1.0 - 1.0/rho_l)/(1.0 - 1.0/rho_spt)
    liq_w = merge([(wspt,SPT_w),(1-wspt,H2O_w)])
    # volume (packing) fraction of grains implied by 80/20 mass split
    f = 1.0/(1.0 + 7.87*0.2/(0.8*rho_l))
    rho_eff = f*7.87 + (1-f)*rho_l
    mix_w = merge([(0.8,ZnWO4_w),(0.2,liq_w)])
    Xm,Xc,Rm,Z = props(mix_w,rho_eff)
    print("rho_liq=%.2f -> grain packing f=%.3f ; rho_eff=%.3f g/cm3"%(rho_l,f,rho_eff))
    print("   X0 = %.2f g/cm2 = %.3f cm  |  Rm = %.2f cm  |  Zeff = %.1f  |  25 X0 = %.1f cm"%(Xm,Xc,Rm,Z,25*Xc))
    print("   mass fractions:", {e:round(v,4) for e,v in sorted(mix_w.items())})
