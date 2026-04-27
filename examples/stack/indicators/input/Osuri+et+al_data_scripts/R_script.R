
library(reshape2)
library(lme4)
library(vegan)
library(MuMIn)

setwd("C:/work_folder/valparai_restoration_assessment/data/data_upload")
traits<-read.csv("species_traits.csv")
Sites<-read.csv("Resto_site_info.csv")
Sites$age<-2017-Sites$Year_restored
Sites$age[Sites$Type=="Benchmark"]<-9999

Dat<-read.csv("tree_data.csv")
Age<-Sites$age[match(Dat$Plot_code,Sites$Plot_code)]
dat<-droplevels(subset(Dat,Remarks!="cut"&Remarks!="dead"&Age>=7))
dat<-droplevels(subset(dat,Plot_code!="drop"))
Regen<-read.csv('regen_data.csv')
Regen$sp_type<-traits$Habt_New[match(Regen$acc_name,traits$acc_name)]

dat$sp_type<-traits$Habt_New[match(dat$accpt.nam,traits$acc_name)]
dat$Can_vis<-Sites$Can_vis[match(dat$Plot_code,Sites$Plot_code)]
dat$Can_den<-Sites$Can_den[match(dat$Plot_code,Sites$Plot_code)]

dat$szclas<-cut(dat$DBH,c(0,15,40,max(dat$DBH)),c("Small","Medium","Large"))
dat$htclas<-cut(dat$Height,c(0,10,20,max(dat$Height,na.rm=T)),c("Small","Medium","Large"))
dat$chave_E<-Sites$Chave_E[match(dat$Plot_code,Sites$Plot_code)]
WD_sp<-traits$Wden_sp[match(dat$accpt.nam,traits$acc_name)]
WD_gen<-traits$Wden_gen[match(dat$accpt.nam,traits$acc_name)]
dat$wden_use<-WD_sp
dat$wden_use[is.na(dat$wden_use)==T]<-WD_gen[is.na(dat$wden_use)==T]
dat$wden_use[is.na(dat$wden_use)==T]<-0.54
dat$mod_ht<-exp(0.893-dat$chave_E+0.760*log(dat$DBH)-0.0340*(log(dat$DBH)^2))
dat$carbon<-0.471*0.0673*(dat$wden_use*dat$DBH^2*ifelse(dat$Remarks=="no height noted",dat$mod_ht,dat$Height))^0.976
dat$HD<-ifelse(dat$HD_include==1,dat$Height/dat$DBH,NA)
dat$logHD<-ifelse(dat$HD_include==1,log(dat$Height)/log(dat$DBH),NA)

Plot<-sort(unique(dat$Plot_code))
Site<-dat$Site_code[match(Plot,dat$Plot_code)]
Treat<-dat$Treatment[match(Plot,dat$Plot_code)]
Stand_Str<-tapply(dat$X,list(dat$Plot_code,dat$szclas),length)

Canopy<-tapply(dat$Can_vis,dat$Plot_code,mean,na.rm=T)
Treeden<-tapply(dat$X,dat$Plot_code,length)
LogHD<-tapply(dat$logHD,dat$Plot_code,mean,na.rm=T)
Carbon<-tapply(dat$carbon,dat$Plot_code,sum,na.rm=T)*100*100/(1000*20*20)
spric<-tapply(dat$X,list(dat$Plot_code,dat$species),length)
spric<-ifelse(is.na(spric)==T,0,1)
Spric<-rowSums(spric)
matSp<-tapply(dat$X[dat$sp_type=="Mature"],list(dat$Plot_code[dat$sp_type=="Mature"],dat$species[dat$sp_type=="Mature"]),length)
matSp<-ifelse(is.na(matSp)==T,0,1)
MatSp<-rowSums(matSp)


sp_site<-acast(dat,Plot_code~species)
Y<-as.matrix(vegdist(sp_site,methd='bray'))
diag(Y)<-NA
INDEX<-dat$Treatment[match(rownames(Y),dat$Plot_code)]
Y1<-Y[INDEX=="Benchmark",]
Dist<-colMeans(Y1,na.rm=T)
Sim<-100*(1-Dist)
Veg_Frame<-data.frame(Plot,Site,Treat,Canopy,Treeden,LogHD,Carbon,Spric,MatSp,Sim)

Regplot<-sort(unique(Regen$Plot_code))
Regsite<-Regen$Site_code[match(Regplot,Regen$Plot_code)]
Regtreat<-Regen$Treatment[match(Regplot,Regen$Plot_code)]

Regden<-tapply(Regen$regen,Regen$Plot_code,sum)
Regden[is.na(Regden)==T]<-0
Regnat<-tapply(Regen$regen[Regen$sp_type!="Int"],Regen$Plot_code[Regen$sp_type!="Int"],sum)
Regnat[is.na(Regnat)==T]<-0

Reginv<-tapply(Regen$regen[Regen$sp_type=="Int"],Regen$Plot_code[Regen$sp_type=="Int"],sum)
Reginv[is.na(Reginv)==T]<-0
Regspr<-tapply(Regen$X,Regen$Plot_code,length)
Regspr[is.na(Regspr)==T]<-0
RegMsp<-tapply(Regen$X[Regen$sp_type=="Mature"],Regen$Plot_code[Regen$sp_type=="Mature"],length)
RegMsp[is.na(RegMsp)==T]<-0
Reg_Frame<-data.frame(Regplot,Regsite,Regtreat,Regden,Regnat,Reginv,Regspr,RegMsp)

Sites_fin<-droplevels(subset(Sites,age>=7))
Sites_fin$Canopy<-Veg_Frame$Canopy[match(Sites_fin$Plot_code,Veg_Frame$Plot)]
Sites_fin$Treeden<-Veg_Frame$Treeden[match(Sites_fin$Plot_code,Veg_Frame$Plot)]
Sites_fin$LogHD<-Veg_Frame$LogHD[match(Sites_fin$Plot_code,Veg_Frame$Plot)]
Sites_fin$Carbon<-Veg_Frame$Carbon[match(Sites_fin$Plot_code,Veg_Frame$Plot)]
Sites_fin$Spric<-Veg_Frame$Spric[match(Sites_fin$Plot_code,Veg_Frame$Plot)]
Sites_fin$MatSp<-Veg_Frame$MatSp[match(Sites_fin$Plot_code,Veg_Frame$Plot)]
Sites_fin$Sim<-Veg_Frame$Sim[match(Sites_fin$Plot_code,Veg_Frame$Plot)]

Sites_fin$Regden<-Reg_Frame$Regden[match(Sites_fin$Plot_code,Reg_Frame$Regplot)]
Sites_fin$Regnat<-Reg_Frame$Regnat[match(Sites_fin$Plot_code,Reg_Frame$Regplot)]
Sites_fin$Reginv<-Reg_Frame$Reginv[match(Sites_fin$Plot_code,Reg_Frame$Regplot)]
Sites_fin$Regspr<-Reg_Frame$Regspr[match(Sites_fin$Plot_code,Reg_Frame$Regplot)]
Sites_fin$Regmsp<-Reg_Frame$RegMsp[match(Sites_fin$Plot_code,Reg_Frame$Regplot)]
Sites_fin$Treat<-ifelse(Sites_fin$Type=="Active","B.AR",ifelse(Sites_fin$Type=="Passive","A.NR","C.BC"))
Sites_fin<-droplevels(subset(Sites_fin,is.na(Treeden)==F))


Sites_trim<-droplevels(subset(Sites_fin,Forest_name!="Stanmore"))
Sites_trim<-droplevels(subset(Sites_trim,Forest_name!="Injiparai"))
#GLMMs and GLMs

pred<-Sites_fin$Treat
Pred<-pred
Pred[Pred=="C.BC"]<-"A.A" 
type<-Sites_fin$Treat
type_lmm<-Sites_fin$Treat[Sites_fin$Type!="Benchmark"]
type_lm<-Sites_fin$Treat[Sites_fin$Type!="Active"]
dist_lmm<-scale(Sites_fin$dist_PA[Sites_fin$Type!="Benchmark"])
rand_lmm<-Sites_fin$Site_code[Sites_fin$Type!="Benchmark"]
rand_lm<-Sites_fin$Site_code[Sites_fin$Type!="Active"]
Rand_lmm<-substr(rand_lmm,1,4)
test<-Sites_fin$Plant_den[Sites_fin$Type!="Benchmark"]

pred_trim<-Sites_trim$Treat
Pred_trim<-pred_trim
Pred_trim[Pred_trim=="C.BC"]<-"A.A" 
type_trim_lmm<-Sites_trim$Treat[Sites_trim$Type!="Benchmark"]
dist_trim_lmm<-scale(Sites_trim$dist_PA[Sites_trim$Type!="Benchmark"])
rand_trim_lmm<-Sites_trim$Site_code[Sites_trim$Type!="Benchmark"]


#Canopy
resp<-cbind(Sites_fin$Canopy,rep(100,nrow(Sites_fin)))
resp_lmm<-resp[Sites_fin$Type!="Benchmark",]
resp_lm<-resp[Sites_fin$Type!="Active",]
M_lmm<-glmer(resp_lmm~type_lmm*dist_lmm+(1|rand_lmm),family='binomial')
R_sq<-r.squaredGLMM(M_lmm)

M_lm<-glm(resp_lm~type_lm,family='binomial')
C_lmm<-summary(M_lmm)$coefficients
C_lm<-summary(M_lm)$coefficients
rec_mn<-C_lmm[2,1]/C_lm[2,1]
rec_lo<-(C_lmm[2,1]-1.96*C_lmm[2,2])/C_lm[2,1]
rec_hi<-(C_lmm[2,1]+1.96*C_lmm[2,2])/C_lm[2,1]
rec_can<-c(rec_mn,rec_lo,rec_hi)

newdat<-expand.grid('type_lmm'=c('A.NR','B.AR'),'dist_lmm'=sort(unique(dist_lmm)))
newdat$predict_lmm<-exp(predict(M_lmm,newdat,re.form=NA))
YLIM<-max(resp,na.rm=T)
YLAB<-expression(paste("Canopy cover (%)"))
par(mar=c(5,5,4,2),cex.lab=1.5,cex.axis=1.2,las=1,bty='n',tck=0.02)
XLIM<-c(-964.6209/600.9225,(2000-964.6209)/600.9225)
XLAB<-"Distance from contiguous forest (m)"
plot(resp_lmm[,1]~dist_lmm, pch=19,col=ifelse(type_lmm=="B.AR",'black','grey70'),cex=1.5,yaxt='n',xaxt='n',xlim=XLIM,ylab=YLAB,xlab=XLAB)
axis(2,seq(-20,100,20),lwd=2,las=1,cex.axis=1.2)
axis(1,(c(-500,0,500,1000,1500,2000)-964.6209)/600.9225,c(NA,0,500,1000,1500,2000),lwd=2,cex.axis=1.2)
points(100*newdat$predict_lmm[newdat$type_lmm=="A.NR"]~newdat$dist_lmm[newdat$type_lmm=="A.NR"],type='l',lwd=4,col='grey70')
points(100*newdat$predict_lmm[newdat$type_lmm=="B.AR"]~newdat$dist_lmm[newdat$type_lmm=="B.AR"],type='l',lwd=4,col='black')

resp_trim<-cbind(Sites_trim$Canopy,rep(100,nrow(Sites_trim)))
resp_trim_lmm<-resp_trim[Sites_trim$Type!="Benchmark",]
M_trim_lmm<-glmer(resp_trim_lmm~type_trim_lmm*dist_trim_lmm+(1|rand_trim_lmm),family='binomial')
R_trim_sq<-r.squaredGLMM(M_trim_lmm)
summary(M_lmm)$coefficients
summary(M_trim_lmm)$coefficients
R_sq
R_trim_sq


#Treeden
resp<-Sites_fin$Treeden
resp_lmm<-resp[Sites_fin$Type!="Benchmark"]
resp_lm<-resp[Sites_fin$Type!="Active"]
M_lmm<-glmer(resp_lmm~type_lmm*dist_lmm+(1|rand_lmm),family='poisson')
R_sq<-r.squaredGLMM(M_lmm)

M_lm<-glm(resp_lm~type_lm,family='poisson')
C_lmm<-summary(M_lmm)$coefficients
C_lm<-summary(M_lm)$coefficients
rec_mn<-C_lmm[2,1]/C_lm[2,1]
rec_lo<-(C_lmm[2,1]-1.96*C_lmm[2,2])/C_lm[2,1]
rec_hi<-(C_lmm[2,1]+1.96*C_lmm[2,2])/C_lm[2,1]
rec_den<-c(rec_mn,rec_lo,rec_hi)

resp_trim<-Sites_trim$Treeden
resp_trim_lmm<-resp_trim[Sites_trim$Type!="Benchmark"]
M_trim_lmm<-glmer(resp_trim_lmm~type_trim_lmm*dist_trim_lmm+(1|rand_trim_lmm),family='poisson')
R_trim_sq<-r.squaredGLMM(M_trim_lmm)
summary(M_lmm)$coefficients
summary(M_trim_lmm)$coefficients
R_sq
R_trim_sq

#Spric
resp<-Sites_fin$Spric
resp_lmm<-resp[Sites_fin$Type!="Benchmark"]
resp_lm<-resp[Sites_fin$Type!="Active"]
M_lmm<-glmer(resp_lmm~type_lmm*dist_lmm+(1|rand_lmm),family='poisson')
R_sq<-r.squaredGLMM(M_lmm)

M_lm<-glm(resp_lm~type_lm,family='poisson')
C_lmm<-summary(M_lmm)$coefficients
C_lm<-summary(M_lm)$coefficients
rec_mn<-C_lmm[2,1]/C_lm[2,1]
rec_lo<-(C_lmm[2,1]-1.96*C_lmm[2,2])/C_lm[2,1]
rec_hi<-(C_lmm[2,1]+1.96*C_lmm[2,2])/C_lm[2,1]
rec_spr<-c(rec_mn,rec_lo,rec_hi)

newdat<-expand.grid('type_lmm'=c('A.NR','B.AR'),'dist_lmm'=sort(unique(dist_lmm)))
newdat$predict_lmm<-exp(predict(M_lmm,newdat,re.form=NA))
YLIM<-max(resp,na.rm=T)
YLAB<-expression(paste("Species density (plot"^"-1",")"))

par(mar=c(5,5,4,2),cex.lab=1.5,cex.axis=1.2,las=1,bty='n',tck=0.02)
XLIM<-c(-964.6209/600.9225,(2000-964.6209)/600.9225)
XLAB<-"Distance from contiguous forest (m)"
plot(resp_lmm~dist_lmm, pch=19,col=ifelse(type_lmm=="B.AR",'black','grey70'),cex=1.5,yaxt='n',xaxt='n',xlim=XLIM,ylab=YLAB,xlab=XLAB)
axis(2,seq(-5,25,5),lwd=2,las=1,cex.axis=1.2)
axis(1,(c(-500,0,500,1000,1500,2000)-964.6209)/600.9225,c(NA,0,500,1000,1500,2000),lwd=2,cex.axis=1.2)
points(newdat$predict_lmm[newdat$type_lmm=="A.NR"]~newdat$dist_lmm[newdat$type_lmm=="A.NR"],type='l',lwd=4,col='grey70')
points(newdat$predict_lmm[newdat$type_lmm=="B.AR"]~newdat$dist_lmm[newdat$type_lmm=="B.AR"],type='l',lwd=4,col='black')

resp_trim<-Sites_trim$Spric
resp_trim_lmm<-resp_trim[Sites_trim$Type!="Benchmark"]
M_trim_lmm<-glmer(resp_trim_lmm~type_trim_lmm*dist_trim_lmm+(1|rand_trim_lmm),family='poisson')
R_trim_sq<-r.squaredGLMM(M_trim_lmm)
summary(M_lmm)$coefficients
summary(M_trim_lmm)$coefficients
R_sq
R_trim_sq


#LS_Spric
resp<-Sites_fin$MatSp
resp_lmm<-resp[Sites_fin$Type!="Benchmark"]
resp_lm<-resp[Sites_fin$Type!="Active"]
M_lmm<-glmer(resp_lmm~type_lmm*dist_lmm+(1|rand_lmm),family='poisson')
R_sq<-r.squaredGLMM(M_lmm)

M_lm<-glm(resp_lm~type_lm,family='poisson')
C_lmm<-summary(M_lmm)$coefficients
C_lm<-summary(M_lm)$coefficients
rec_mn<-C_lmm[2,1]/C_lm[2,1]
rec_lo<-(C_lmm[2,1]-1.96*C_lmm[2,2])/C_lm[2,1]
rec_hi<-(C_lmm[2,1]+1.96*C_lmm[2,2])/C_lm[2,1]
rec_msp<-c(rec_mn,rec_lo,rec_hi)

newdat<-expand.grid('type_lmm'=c('A.NR','B.AR'),'dist_lmm'=sort(unique(dist_lmm)))
newdat$predict_lmm<-exp(predict(M_lmm,newdat,re.form=NA))
YLIM<-max(resp,na.rm=T)
YLAB<-expression(paste("LS Species density (plot"^"-1",")"))

par(mar=c(5,5,4,2),cex.lab=1.5,cex.axis=1.2,las=1,bty='n',tck=0.02)
XLIM<-c(-964.6209/600.9225,(2000-964.6209)/600.9225)
XLAB<-"Distance from contiguous forest (m)"
plot(resp_lmm~dist_lmm, pch=19,col=ifelse(type_lmm=="B.AR",'black','grey70'),cex=1.5,yaxt='n',xaxt='n',xlim=XLIM,ylab=YLAB,xlab=XLAB)
axis(2,seq(-3,12,3),lwd=2,las=1,cex.axis=1.2)
axis(1,(c(-500,0,500,1000,1500,2000)-964.6209)/600.9225,c(NA,0,500,1000,1500,2000),lwd=2,cex.axis=1.2)
points(newdat$predict_lmm[newdat$type_lmm=="A.NR"]~newdat$dist_lmm[newdat$type_lmm=="A.NR"],type='l',lwd=4,col='grey70')
points(newdat$predict_lmm[newdat$type_lmm=="B.AR"]~newdat$dist_lmm[newdat$type_lmm=="B.AR"],type='l',lwd=4,col='black')

resp_trim<-Sites_trim$MatSp
resp_trim_lmm<-resp_trim[Sites_trim$Type!="Benchmark"]
M_trim_lmm<-glmer(resp_trim_lmm~type_trim_lmm*dist_trim_lmm+(1|rand_trim_lmm),family='poisson')
R_trim_sq<-r.squaredGLMM(M_trim_lmm)
summary(M_lmm)$coefficients
summary(M_trim_lmm)$coefficients
R_sq
R_trim_sq

#Reg_den
resp<-Sites_fin$Regden
resp_lmm<-resp[Sites_fin$Type!="Benchmark"]
resp_lm<-resp[Sites_fin$Type!="Active"]
M_lmm<-glmer(resp_lmm~type_lmm*dist_lmm+(1|rand_lmm),family='poisson')
R_sq<-r.squaredGLMM(M_lmm)
YLIM<-max(resp_lmm,na.rm=T)
YLAB<-expression(paste("Juvenile tree density (plot"^"-1",")"))

M_lm<-glm(resp_lm~type_lm,family='poisson')
C_lmm<-summary(M_lmm)$coefficients
C_lm<-summary(M_lm)$coefficients
rec_mn<-C_lmm[2,1]/C_lm[2,1]
rec_lo<-(C_lmm[2,1]-1.96*C_lmm[2,2])/C_lm[2,1]
rec_hi<-(C_lmm[2,1]+1.96*C_lmm[2,2])/C_lm[2,1]
rec_reg<-c(rec_mn,rec_lo,rec_hi)


resp_trim<-Sites_trim$Regden
resp_trim_lmm<-resp_trim[Sites_trim$Type!="Benchmark"]
M_trim_lmm<-glmer(resp_trim_lmm~type_trim_lmm*dist_trim_lmm+(1|rand_trim_lmm),family='poisson')
R_trim_sq<-r.squaredGLMM(M_trim_lmm)
summary(M_lmm)$coefficients
summary(M_trim_lmm)$coefficients
R_sq
R_trim_sq

#Reg_nat
resp<-cbind(Sites_fin$Regnat,Sites_fin$Regden)
resp_lmm<-resp[Sites_fin$Type!="Benchmark",]
resp_lm<-resp[Sites_fin$Type!="Active",]
M_lmm<-glmer(resp_lmm~type_lmm*dist_lmm+(1|rand_lmm),family='binomial')
R_sq<-r.squaredGLMM(M_lmm)

M_lm<-glm(resp_lm~type_lm,family='binomial')
C_lmm<-summary(M_lmm)$coefficients
C_lm<-summary(M_lm)$coefficients
rec_mn<-C_lmm[2,1]/C_lm[2,1]
rec_lo<-(C_lmm[2,1]-1.96*C_lmm[2,2])/C_lm[2,1]
rec_hi<-(C_lmm[2,1]+1.96*C_lmm[2,2])/C_lm[2,1]
rec_nat<-c(rec_mn,rec_lo,rec_hi)

resp_trim<-cbind(Sites_trim$Reginv,Sites_trim$Regden)
resp_trim_lmm<-resp_trim[Sites_trim$Type!="Benchmark",]
M_trim_lmm<-glmer(resp_trim_lmm~type_trim_lmm*dist_trim_lmm+(1|rand_trim_lmm),family='binomial')
R_trim_sq<-r.squaredGLMM(M_trim_lmm)
summary(M_lmm)$coefficients
summary(M_trim_lmm)$coefficients
R_sq
R_trim_sq

#Reg Spric
resp<-Sites_fin$Regspr
resp_lmm<-resp[Sites_fin$Type!="Benchmark"]
resp_lm<-resp[Sites_fin$Type!="Active"]
M_lmm<-glmer(resp_lmm~type_lmm*dist_lmm+(1|rand_lmm),family='poisson')
R_sq<-r.squaredGLMM(M_lmm)

M_lm<-glm(resp_lm~type_lm,family='poisson')
C_lmm<-summary(M_lmm)$coefficients
C_lm<-summary(M_lm)$coefficients
rec_mn<-C_lmm[2,1]/C_lm[2,1]
rec_lo<-(C_lmm[2,1]-1.96*C_lmm[2,2])/C_lm[2,1]
rec_hi<-(C_lmm[2,1]+1.96*C_lmm[2,2])/C_lm[2,1]
rec_regsp<-c(rec_mn,rec_lo,rec_hi)

resp_trim<-Sites_trim$Regspr
resp_trim_lmm<-resp_trim[Sites_trim$Type!="Benchmark"]
M_trim_lmm<-glmer(resp_trim_lmm~type_trim_lmm*dist_trim_lmm+(1|rand_trim_lmm),family='poisson')
R_trim_sq<-r.squaredGLMM(M_trim_lmm)
summary(M_lmm)$coefficients
summary(M_trim_lmm)$coefficients
R_sq
R_trim_sq

#Reg LS Spric
resp<-Sites_fin$Regmsp
resp_lmm<-resp[Sites_fin$Type!="Benchmark"]
resp_lm<-resp[Sites_fin$Type!="Active"]
M_lmm<-glmer(resp_lmm~type_lmm*dist_lmm+(1|rand_lmm),family='poisson')
R_sq<-r.squaredGLMM(M_lmm)
YLIM<-max(resp_lmm,na.rm=T)
YLAB<-expression(paste("LS sapling species density (plot"^"-1",")"))

M_lm<-glm(resp_lm~type_lm,family='poisson')
C_lmm<-summary(M_lmm)$coefficients
C_lm<-summary(M_lm)$coefficients
rec_mn<-C_lmm[2,1]/C_lm[2,1]
rec_lo<-(C_lmm[2,1]-1.96*C_lmm[2,2])/C_lm[2,1]
rec_hi<-(C_lmm[2,1]+1.96*C_lmm[2,2])/C_lm[2,1]
rec_regms<-c(rec_mn,rec_lo,rec_hi)

newdat<-expand.grid('type_lmm'=c('A.NR','B.AR'),'dist_lmm'=sort(unique(dist_lmm)))
newdat$predict_lmm<-exp(predict(M_lmm,newdat,re.form=NA))

par(mar=c(5,5,4,2),cex.lab=1.5,cex.axis=1.2,las=1,bty='n',tck=0.02)
XLIM<-c(-964.6209/600.9225,(2000-964.6209)/600.9225)
XLAB<-"Distance from contiguous forest (m)"
plot(resp_lmm~dist_lmm, pch=19,col=ifelse(type_lmm=="B.AR",'black','grey70'),cex=1.5,yaxt='n',xaxt='n',xlim=XLIM,ylab=YLAB,xlab=XLAB)
axis(2,seq(-2,8,2),lwd=2,las=1,cex.axis=1.2)
axis(1,(c(-500,0,500,1000,1500,2000)-964.6209)/600.9225,c(NA,0,500,1000,1500,2000),lwd=2,cex.axis=1.2)
points(newdat$predict_lmm[newdat$type_lmm=="A.NR"]~newdat$dist_lmm[newdat$type_lmm=="A.NR"],type='l',lwd=4,col='grey70')
points(newdat$predict_lmm[newdat$type_lmm=="B.AR"]~newdat$dist_lmm[newdat$type_lmm=="B.AR"],type='l',lwd=4,col='black')
legend('topleft',pch=c(19,19),lty=1,lwd=3,c('NR','AR'),col=c('grey70', 'black'),bty='n',cex=1.5)

resp_trim<-Sites_trim$Regmsp
resp_trim_lmm<-resp_trim[Sites_trim$Type!="Benchmark"]
M_trim_lmm<-glmer(resp_trim_lmm~type_trim_lmm*dist_trim_lmm+(1|rand_trim_lmm),family='poisson')
R_trim_sq<-r.squaredGLMM(M_trim_lmm)
summary(M_lmm)$coefficients
summary(M_trim_lmm)$coefficients
R_sq
R_trim_sq

#Similarity
resp<-Sites_fin$Sim
resp_lmm<-resp[Sites_fin$Type!="Benchmark"]
resp_lm<-resp[Sites_fin$Type!="Active"]
M_lmm<-lmer(resp_lmm~type_lmm*dist_lmm+(1|rand_lmm))
R_sq<-r.squaredGLMM(M_lmm)
YLIM<-max(resp_lmm,na.rm=T)
YLAB<-expression(paste("Similarity to benchmark rainforest (%)"))

M_lm<-lm(resp_lm~type_lm)
C_lmm<-summary(M_lmm)$coefficients
C_lm<-summary(M_lm)$coefficients
rec_mn<-C_lmm[2,1]/C_lm[2,1]
rec_lo<-(C_lmm[2,1]-1.96*C_lmm[2,2])/C_lm[2,1]
rec_hi<-(C_lmm[2,1]+1.96*C_lmm[2,2])/C_lm[2,1]
rec_sim<-c(rec_mn,rec_lo,rec_hi)
newdat<-expand.grid('type_lmm'=c('A.NR','B.AR'),'dist_lmm'=sort(unique(dist_lmm)))
newdat$predict_lmm<-predict(M_lmm,newdat,re.form=NA)

par(mar=c(5,5,4,2),cex.lab=1.5,cex.axis=1.2,las=1,bty='n',tck=0.02)
XLIM<-c(-964.6209/600.9225,(2000-964.6209)/600.9225)
XLAB<-"Distance from contiguous forest (m)"
plot(resp_lmm~dist_lmm, pch=19,col=ifelse(type_lmm=="B.AR",'black','grey70'),cex=1.5,yaxt='n',xaxt='n',xlim=XLIM,ylab=YLAB,xlab=XLAB)
axis(2,seq(-4,24,4),lwd=2,las=1,cex.axis=1.2)
axis(1,(c(-500,0,500,1000,1500,2000)-964.6209)/600.9225,c(NA,0,500,1000,1500,2000),lwd=2,cex.axis=1.2)
points(newdat$predict_lmm[newdat$type_lmm=="A.NR"]~newdat$dist_lmm[newdat$type_lmm=="A.NR"],type='l',lwd=4,col='grey70')
points(newdat$predict_lmm[newdat$type_lmm=="B.AR"]~newdat$dist_lmm[newdat$type_lmm=="B.AR"],type='l',lwd=4,col='black')

resp_trim<-Sites_trim$Sim
resp_trim_lmm<-resp_trim[Sites_trim$Type!="Benchmark"]
M_trim_lmm<-lmer(resp_trim_lmm~type_trim_lmm*dist_trim_lmm+(1|rand_trim_lmm))
R_trim_sq<-r.squaredGLMM(M_trim_lmm)
summary(M_lmm)$coefficients
summary(M_trim_lmm)$coefficients
R_sq
R_trim_sq

#logHD
resp<-Sites_fin$LogHD
resp_lmm<-resp[Sites_fin$Type!="Benchmark"]
resp_lm<-resp[Sites_fin$Type!="Active"]
M_lmm<-lmer(resp_lmm~type_lmm*dist_lmm+(1|rand_lmm))
R_sq<-r.squaredGLMM(M_lmm)

M_lm<-lm(resp_lm~type_lm)
C_lmm<-summary(M_lmm)$coefficients
C_lm<-summary(M_lm)$coefficients
rec_mn<-C_lmm[2,1]/C_lm[2,1]
rec_lo<-(C_lmm[2,1]-1.96*C_lmm[2,2])/C_lm[2,1]
rec_hi<-(C_lmm[2,1]+1.96*C_lmm[2,2])/C_lm[2,1]
rec_lhd<-c(rec_mn,rec_lo,rec_hi)

resp_trim<-Sites_trim$LogHD
resp_trim_lmm<-resp_trim[Sites_trim$Type!="Benchmark"]
M_trim_lmm<-lmer(resp_trim_lmm~type_trim_lmm*dist_trim_lmm+(1|rand_trim_lmm))
R_trim_sq<-r.squaredGLMM(M_trim_lmm)
summary(M_lmm)$coefficients
summary(M_trim_lmm)$coefficients
R_sq
R_trim_sq

#Carbon
resp<-log(Sites_fin$Carbon)
resp_lmm<-resp[Sites_fin$Type!="Benchmark"]
resp_lm<-resp[Sites_fin$Type!="Active"]
M_lmm<-lmer(resp_lmm~type_lmm*dist_lmm+(1|rand_lmm))
R_sq<-r.squaredGLMM(M_lmm)

M_lm<-lm(resp_lm~type_lm)
C_lmm<-summary(M_lmm)$coefficients
C_lm<-summary(M_lm)$coefficients
rec_mn<-C_lmm[2,1]/C_lm[2,1]
rec_lo<-(C_lmm[2,1]-1.96*C_lmm[2,2])/C_lm[2,1]
rec_hi<-(C_lmm[2,1]+1.96*C_lmm[2,2])/C_lm[2,1]
rec_car<-c(rec_mn,rec_lo,rec_hi)

resp_trim<-log(Sites_trim$Carbon)
resp_trim_lmm<-resp_trim[Sites_trim$Type!="Benchmark"]
M_trim_lmm<-lmer(resp_trim_lmm~type_trim_lmm*dist_trim_lmm+(1|rand_trim_lmm))
R_trim_sq<-r.squaredGLMM(M_trim_lmm)
summary(M_lmm)$coefficients
summary(M_trim_lmm)$coefficients
R_sq
R_trim_sq

Recover<-data.frame(rbind(rec_can,rec_den,rec_lhd,rec_spr,rec_msp,rec_sim,rec_reg,rec_nat,rec_regsp,rec_regms,rec_car))*100
names(Recover)<-c("Mean","LowCI","HiCI")
Recover$Response<-c("Canopy cover","Tree density","Log HD","Species density","LS species\ndensity","Community\nsimilarity","Sapling density","Sapling native\nfraction","Sapling species\ndensity","Sapling LS\nspecies density","Carbon storage")
Cols<-c(rep('grey60',2),'grey90',rep('grey60',4),'grey90',rep('grey60',3))

par(mar=c(5,5,4,2),cex.lab=1.5,cex.axis=1.2,las=1,bty='n',tck=0.02)
bar<-barplot(Recover$Mean,ylim=c(-70,100),col=Cols,yaxt='n',las=1,ylab="% recovery")
text(bar,rep(-30,length(Recover$Mean)),Recover$Response,cex=1.6,srt=90)
axis(2,seq(-25,100,25),lwd=2,las=1)
abline(0,0,lwd=2)
abline(100,0,lty=2,lwd=2)
