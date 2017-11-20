var map ="",latitude ="",longitude="",mapinited=false;
var lnglatXY;
var gpsToGcj = {
	pi : 3.14159265358979324,
	a : 6378245.0,
	ee : 0.00669342162296594323,
	
	geoTransform : function(wgLat, wgLng) {
		var transCoords = {};
		if (this.regionOfChina(wgLat, wgLng)) {
			transCoords["latitude"] = wgLat;
			transCoords["longitude"] = wgLng;
			return transCoords;
		}
		var dLat = this.transformLat(wgLng - 105.0, wgLat - 35.0);
		var dLng = this.transformLng(wgLng - 105.0, wgLat - 35.0);
		var radLat = wgLat / 180.0 * this.pi;
		var magic = Math.sin(radLat);
		magic = 1 - this.ee * magic * magic;
		var sqrtMagic = Math.sqrt(magic);
		dLat = (dLat * 180.0) / ((this.a * (1 - this.ee)) / (magic * sqrtMagic) * this.pi);
		dLng = (dLng * 180.0) / (this.a / sqrtMagic * Math.cos(radLat) * this.pi);
		transCoords["latitude"] = wgLat + dLat;
		transCoords["longitude"] = wgLng + dLng;
		return transCoords;
	},
	
	regionOfChina : function(lat, lng) {
		if (lng < 72.004 || lng > 137.8347) {
			return true;
		} else if (lat < 0.8293 || lat > 55.8271) {
			return true;
		} else {
			return false;
		}
	},
	
	transformLat : function(x, y) {
		var ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * Math.sqrt(Math.abs(x));
		ret += (20.0 * Math.sin(6.0 * x * this.pi) + 20.0 * Math.sin(2.0 * x * this.pi)) * 2.0 / 3.0;
		ret += (20.0 * Math.sin(y * this.pi) + 40.0 * Math.sin(y / 3.0 * this.pi)) * 2.0 / 3.0;
		ret += (160.0 * Math.sin(y / 12.0 * this.pi) + 320 * Math.sin(y * this.pi / 30.0)) * 2.0 / 3.0;
		return ret;
	},
	
	transformLng : function(x, y) {
		var ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * Math.sqrt(Math.abs(x));
		ret += (20.0 * Math.sin(6.0 * x * this.pi) + 20.0 * Math.sin(2.0 * x * this.pi)) * 2.0 / 3.0;
		ret += (20.0 * Math.sin(x * this.pi) + 40.0 * Math.sin(x / 3.0 * this.pi)) * 2.0 / 3.0;
		ret += (150.0 * Math.sin(x / 12.0 * this.pi) + 300.0 * Math.sin(x / 30.0 * this.pi)) * 2.0 / 3.0;
		return ret;
	} 
}

function initmap() {
	map = new AMap.Map('container', {
		zoom : 17,
		resizeEnable : true
	});
	mapinited = true;
}

function gps() {
	// if (typeof wx != "undefined") {// 微信获取定位
	// 	try {
	// 		wx.error(function(res) {
	// 			getGPS();
	// 		});
	// 		wx.ready(function() {
	// 			wx.getLocation({
	// 				type : 'gcj02',
	// 				success : function(res) {
	// 					// res.longitude ; 经度，浮点数，范围为180 ~ -180。
	// 					// res.latitude; 纬度，浮点数，范围为90 ~ -90
	// 					convert2amap(res.longitude, res.latitude, "amap");
	// 				},
	// 				fail : function() {
	// 					getGPS();
	// 				}
	// 			});
	// 		});
	// 	} catch (e) {
	// 		getGPS();
	// 	}
	// } else if (typeof dd != "undefined") {// 钉钉获取定位
	// 	try {
	// 		dd.error(function(error) {
	// 			getGPS();
	// 		});
	// 		dd.ready(function() {
	// 			dd.device.geolocation.get({
	// 				onSuccess : function(result) {
	// 					if (result.location) {
	// 						longitude = result.location.longitude;
	// 						latitude = result.location.latitude;
	// 					} else {
	// 						longitude = result.longitude;
	// 						latitude = result.latitude;
	// 					}

	// 					/* android2.1及之前版本返回的数据会多嵌套一层location,2.2版本会改成和ios一致，请注意，建议对返回的数据先判断存在location，做向后兼容处理 */
	// 					/* 目前androidJSAPI返回的坐标是高德坐标，ios是标准坐标，如果服务端调用的是高德API，则需要多ios返回的经纬度做下处理，详细请见http://lbsbbs.amap.com/forum.php?mod=viewthread&tid=724&page=2 */
	// 					/*
	// 					 * 坐标转换API
	// 					 * http://lbs.amap.com/api/javascript-api/example/p/1602-2/
	// 					 */
	// 					var u = navigator.userAgent;
	// 					var isAndroid = u.indexOf('Android') > -1 || u.indexOf('Linux') > -1; // android终端或者uc浏览器
	// 					var isiOS = !!u.match(/\(i[^;]+;( U;)? CPU.+Mac OS X/); // ios终端
	// 					if (isAndroid) {
	// 						convert2amap(longitude, latitude, "amap");
	// 					} else if (isiOS) {
	// 						convert2amap(longitude, latitude, "");
	// 					}
	// 				},
	// 				onFail : function(err) {
	// 					getGPS();
	// 				}
	// 			});
	// 		});
	// 	} catch (e) {
	// 		getGPS();
	// 	}
	// } else {
	// 	getGPS();
    // }
    getGPS();
}
gps();

/**
 * 通过浏览器获取定位
 */
function getGPS() {
    convert2amap(0, 0, "");
    //alert("123")
    /*
	if (navigator.geolocation) {
		navigator.geolocation.getCurrentPosition(function(position) {
			longitude = position.coords.longitude;
			latitude = position.coords.latitude;
			convert2amap(longitude, latitude, "");
		}, onError);
	} else {
		alert("提示：您的客户端不支持获取定位信息，请升级或联系管理员！");
	}*/
}

function onError(error) {
	switch (error.code) {
	case 1:
		alert("位置服务被拒绝");
		break;
	case 2:
		handleH5ForIOS10();
		// alert("暂时获取不到位置信息");
		break;
	case 3:
		alert("获取信息超时");
		break;
	case 4:
		alert("未知错误");
		break;
	default:
		alert(JSON.stringify(error));
		break;
	}
}

function handleH5ForIOS10() {
	var geolocation = new qq.maps.Geolocation("I44BZ-QZCKW-N6QRI-R5I4U-7COW5-DJBWB", "qqkey");
	geolocation.getLocation(function(position) {
		convert2amap(position.lng, position.lat, "amap");
	}, function() {
		alert("暂时获取不到位置信息！");
	}, {
		timeout : 8000
	});
}

function convert2amap(lng, lat, converttype) {
	if (converttype == "") {
		var gcj = gpsToGcj.geoTransform(lat, lng);
		setLngLat(gcj.longitude, gcj.latitude);
	} else {
		setLngLat(lng, lat);
	}
}

function geocoder() {
	var MGeocoder;
	// 加载地理编码插件
	map.plugin([ "AMap.Geocoder" ], function() {
		MGeocoder = new AMap.Geocoder({
			radius : 1000,
			extensions : "all"
		});
		// 返回地理编码结果
		AMap.event.addListener(MGeocoder, "complete", function(data) {
			var address = data.regeocode.formattedAddress;
			$("#address").val(address);
			$(".refresh-map").html("重新定位");
			$(".address").html("<span style='color:#b0b0b0;'>我在 &lt;</span> " + address + " <span style='color:#b0b0b0;'>&gt; 附近</span>");
		});
		// 逆地理编码
		MGeocoder.getAddress(lnglatXY);
	});
	var marker = new AMap.Marker({
		map : map,
		position : lnglatXY
	});
	marker.setLabel({
		offset : new AMap.Pixel(-13, -30),// 修改label相对于maker的位置
		content : "定位点"
	});
}
function setLngLat(lng, lat) {
	lng=120.434+Math.random().toString(10).substr(2,3);
	lat=31.323+Math.random().toString(10).substr(2,3);
	$(document).ready(function() {
		$("#lng").val(lng);
		$("#lat").val(lat);
	});

	var locationInterval = setInterval(function() {
		if (mapinited) {
			map.clearMap();
			map.setCenter([ lng, lat ]);
			lnglatXY = new AMap.LngLat(lng, lat);
			geocoder();
			clearInterval(locationInterval);
		}
	}, 100);
}

$(function(){
	if(btnType==1)
		changeSignBtn('signin');
	else if(btnType==2)
		changeSignBtn('signout');
	else if(btnType==3){
		$(".sign-load-btn").html("非工作日");
	}else if(btnType==4){
		$(".sign-load-btn").html("无用户ID");
	}
 
	function ajaxSmt(operate){
	 	$("#signForm").ajaxSubmit({
			url: contextPath + "/wxclient/app/attendance/addForEc",
			data:{"operate":operate},
			dataType: "json",
			contentType: "application/x-www-form-urlencoded; charset=utf-8", 
			success:function(data){ 
				if(data.success ) {
					if(data.btnType==1)
						changeSignBtn('signin');
					else if(data.btnType==2)
						changeSignBtn('signout');
					
					var signTime=data.signTime;
					if(operate=="signin"){
						$("#signTime").val(signTime);
						$(".last-signin").find("span:last").text(signTime);
					}else if(operate=="signout"){
						$(".last-signout").find("span:last").text(signTime);
					}
					var info="<table><tr><th colspan='2'>"+data.msg+"</th></tr><tr><td style='width:33%;'>考勤位置:</td><td>"+$("#address").val()+"</td><tr><td>考勤时间:</td><td>"+signTime+"</td></tr></table>"
					showModel(info);
					return false;
					
				}else{
				 	showModel(data.msg);
				 	if(data.btnType==1)
						changeSignBtn('signin');
					else if(data.btnType==2)
						changeSignBtn('signout');
					return false;
				}
			}
		});
	  }
	 
	 //改变签到，签退按钮
	 function changeSignBtn(operate){
		 if(operate=="signin"){
				$(".sign-btn-css").html("签 到");
		}else if(operate=="signout"){
			$(".sign-btn-css").html("签 退");
		}
		
		$(".sign-btn-css").on("click",function(){
			var lng=$("#lng").val(),lat=$("#lat").val(), address=$("#address").val();
			if(lng=="" || lat=="" || address==""){
				showModel("请确认是否获取到了位置");
				return false;
			}
			$(this).html("加载中...").unbind("click");
			ajaxSmt(operate);
		});
	 }
	 
	 //弹出提示小窗口
	 function showModel(info){
		$(".weui_dialog_bd").html(info);
		$(".weui_dialog_alert").show();
	}
	 
	 $(".weui_btn_dialog").on("click",function(){
		 $(".weui_dialog_alert").hide();
	 })
   	
	//提示窗口
	$(".modal-button-bold").click(function(){
		$('div.modal').removeClass('modal-in');
		$('div.modal-overlay').removeClass('modal-overlay-visible');
	});
			
	$(".sign-help").on("click",function(){
		$(".sign-page")
		.hide()
		.prev()
		.show();
	});
			
	$(".help-back").on("click",function(){
		$(".sign-help-page")
		.hide()
		.next()
		.show();
	})
	
	$(".refresh-map").on("click",function(){
		$(this).html("正在定位...");
		gps();
	})
	
	setInterval(gps,30000);
	/*
	if (typeof wx != "undefined") {// 针对企业微信有时进入页面需要刷新才能定位的问题
		setTimeout(function() {
			var lng=$("#lng").val(),lat=$("#lat").val(), address=$("#address").val();
			if(lng=="" || lat=="" || address==""){
				window.location.reload();
			}
		}, 5000);
	} else if (typeof dd != "undefined") {// 针对钉钉JSAPI在4g定位下很慢的问题
		setTimeout(function() {
			var lng=$("#lng").val(),lat=$("#lat").val(), address=$("#address").val();
			if(lng=="" || lat=="" || address==""){
				getGPS();
			}
		}, 5000);
	}*/
});
