<!-- source: MinerU_markdown_2025年美赛A题完整论文—郭老师_20260125140854_2015305855361236992.md; mode: auto->bishe ; lines: 706-833 -->

# 5.1 模型的优点

（1）采用数据驱动的分析方法，运用结构光扫描仪进行非侵入性测量，获取楼梯表面情况的实际数据，为模型的建立提供了可靠的数据基础，显著提高了分析的准确性。

（2）应用可视化技术，通过绘制热力图和3D表面图，将楼梯的磨损情况直观地展示出来，极大地方便了对数据的理解和分析。

（3）充分考虑多种因素，除了使用年限和人流量外，还综合材料特性和表面磨损情况进行分析，使分析结果更加全面、准确。

（4）选用经典的阿基米德磨损模型进行分析，该模型在描述磨损速率方面具有一定的普适性和准确性，提升了模型的可靠性。

（5）进行动态分析，充分考虑上下楼时不同的力学关系，对楼梯的磨损进行动态研究，使分析结果更贴近实际情况。

（6）借助蒙特卡罗仿真进行磨损预测，能够模拟不同使用情况下的磨损情况，为磨损预测提供了一种灵活、有效的方法。

# 5.2 模型的不足

（1）为了追求精确度和真实性，使用了较为复杂的数学模型，具有一定的复杂性，在进行聚类分析和蒙特卡罗仿真时，可能需要复杂的计算和专业知识，对初次使用的考古学家有一定难度。

（2）由于数据有限，忽略了环境因素，在分析磨损时，没有考虑天气、湿度等环境因素对材料磨损的影响，可能影响模型分析结果的准确性。

（3）实际应用存在局限，尽管模型在理论上具有一定的普适性，但在实际应用中可能需要针对更加复杂的情况调整模型参数，增加了应用的复杂度。

# 参考文献



[1] Di Giovanni A, Todaro C, Cardu M, et al. Laboratory test campaign aimed at the analysis of an uncommon wear phenomenon in a marble quarry[J]. Applied Sciences, 2022, 12(4): 2264.





[2] Li J, Zheng X. Experimental investigation of the stepping dynamics of upstairs walking under time pressure[J]. Physica A: Statistical Mechanics and its Applications, 2023, 622: 128829.





[3] 刘喜明, 郭占田, 于长山, 等. 摩擦磨损中的马氏体相变及其对材料磨损特性的影响





[J].金属热处理,1997(3):8-12.





[4]田晓，贾克军，祝彦，等.陶瓷材料磨损机制及磨损程度评价方法综述[J].润滑与密封,2012,37(1):105-109.





[5] He L, Fan W, Dai Z, et al. A Human-Machine-Environment Interactive Measurement System for Non-Anthropomorphic Exoskeletons[J]. IEEE Transactions on Instrumentation and Measurement, 2023.



# 附录

<table><tr><td>求解代码</td></tr><tr><td>2.3.聚类分析</td></tr><tr><td>% 读取图像</td></tr><tr><td>image = imread(&#x27;jly.png&#x27;);</td></tr><tr><td>% 如果是彩色图像，转换为灰度图像</td></tr><tr><td>if size(image, 3) == 3</td></tr><tr><td>image = rgb2gray(image);</td></tr><tr><td>end</td></tr><tr><td>% 对图像数据进行归一化处理（可选，根据数据情况决定是否需要）</td></tr><tr><td>image = im2double(image);</td></tr><tr><td>% 展平图像数据，方便进行聚类</td></tr><tr><td>flat_image = reshape(image, [], 1);</td></tr><tr><td>% 设定聚类数量，这里先假设聚类为3类，可根据实际情况调整</td></tr><tr><td>num_clusters = 2;</td></tr><tr><td>% 使用k-means聚类算法</td></tr><tr><td>[ idx, C] = kmeans-flat_image, num_clusters);</td></tr><tr><td>% 将聚类结果重新恢复为图像的二维形状</td></tr><tr><td>cluster_labels = reshape(idx, size(image));</td></tr><tr><td>% 假设数值最小的聚类可能对应谷（需根据实际情况调整判断逻辑）</td></tr><tr><td>min_cluster_value = min(cluster_labels());</td></tr><tr><td>valley_mask = cluster_labels == min_cluster_value;</td></tr><tr><td>% 进行形态学闭运算以连接可能的谷区域（可选，根据情况调整）</td></tr><tr><td>se = strel(&#x27;disk&#x27;, 15);</td></tr><tr><td>valley_mask Closed = inclose(valley_mask, se);</td></tr><tr><td>% 标记连通区域</td></tr><tr><td>[labeled_valleys, num_valleys] = bwblabel(valley_mask Closed);</td></tr><tr><td>fprintf(&#x27;谷的数量:%d\n&#x27;, num_valleys);</td></tr><tr><td>% 可视化聚类结果（可选）</td></tr><tr><td>figure;</td></tr><tr><td>imshow(3-cluster_labels, [];</td></tr><tr><td>title(&#x27;聚类结果&#x27;);</td></tr><tr><td>2.4-2.5仿真预测</td></tr><tr><td>% 参数设置</td></tr></table>

```txt
friction_displacement  $= 0.1 / 100$ $\%$  转换为米（  $0.1\mathrm{cm}\rightarrow 0.001\mathrm{m})$    
wear_coefficient  $= 0.000876$ $\%$  磨损系数，单位：  $\mathrm{mm}^{\wedge}2 / (\mathrm{N}\cdot \mathrm{m})$    
usage_year  $= 50$ $\%$  使用年限为50年  
monthly_users_range  $= [1900,2100]$ $\%$  每月使用人数范围  
weight_mean  $= 80$ $\%$  体重均值 (kg)  
weight_std  $= 5$ $\%$  体重标准差 (kg)  
up_stair-multiplier  $= 1.1$ $\%$  上楼梯倍数  
down_stair-multiplier  $= 1.1$ $\%$  下楼梯倍数  
 $\%$  总月数（50年）  
total_months  $=$  usage_year \* 12;  
 $\%$  初始化变量  
total_wear_volume  $= 0$ $\%$  总磨损体积  
monthly_wear_volume  $=$  zeros(1,total Months);  $\%$  存储每月的磨损体积  
 $\%$  MonteCarlo仿真  
for month  $= 1:$  total_monthsnannual_wear  $= 0$ $\%$  每月磨损体积初始化days_in_month  $= 30$ $\%$  假设每个月30天（可根据需要调整）for day  $= 1:$  days_in_month $\%$  随机生成今天的使用人数current_users  $=$  randi(monthly_users_range); $\%$  随机生成每个用户的体重，符合正态分布currentweights  $=$  normrnd(weight_mean,weight_std,[current_users,1]); $\%$  随机生成每个用户是上楼梯还是下楼梯（  $50 \%$  的概率）up_down_stairs  $=$  rand(current_users,1)>0.5；  $\% 0$  表示下楼梯，1表  
示上楼梯 $\%$  计算每个用户的磨损力（  $\mathbb{F} = \mathbb{mg}$  force  $=$  currentweights  $*9.81$ $\% \mathrm{N}$  （牛顿） $\%$  计算每个用户的磨损体积for i  $= 1:$  current_usersif up_down_stairs(i)  $= = 1$ $\%$  上楼梯annual_wear  $=$  annual_wear  $+$  force(i)\*up_stair-multiplier\* friction_displacement \* wear_coefficient;else  $\%$  下楼梯annual_wear  $=$  annual_wear  $+$  force(i)\*down_stair-multiplier\* friction_displacement \* wear_coefficient;endend
```

```matlab
$\%$  每月磨损体积 monthly_wear_volume(month)  $=$  annual_wear \*1e2;  $\%$  转换为mm^3 total_wear_volume  $=$  total_wear_volume  $+$  annual_wear;  $\%$  累积总磨损体  
积 end  
 $\%$  输出最终的磨损体积（单位：  $\mathrm{mm}^{\wedge}3$  ）  
fprintf('该台阶的总磨损体积为：  $\% .4\mathrm{f}\mathrm{mm}^{\wedge}3\backslash \mathrm{n}^{\prime}$  ,total_wear_volume \*1e2);   
 $\%$  可视化：每月的磨损和累计磨损体积 months  $= 1$  :total_months; figure; subplot(1,2,1); plot(months,monthly_wear_volume,'-o','LineWidth',2,'MarkerSize',6);xlabel('月份');ylabel('每月磨损体积(mm^3)"); title('每月磨损体积'); grid on;  $\% \%$  subplot(1,2,2); plot(months,cumsum(monthly_wear_volume),'-o','LineWidth',2,'MarkerSize',6);xlabel('月份');ylabel('累计磨损体积(mm^3)'); title('累计磨损体积');grid on;   
2.6修复区分聚类   
 $\%$  读取图片 img  $=$  imread('xf3.png');  $\%$  请确保图像路径正确   
 $\%$  转换为RGB并归一化到[0,1] imgrgb  $=$  im2double(img);   
 $\%$  获取图像尺寸 [rows,cols,channels]  $=$  size(img rgb); split_column  $=$  roundcols/2);   
 $\%$  创建标签图像，将竖直线左边区域标为1，右边区域标为2 labels  $=$  ones Rows, cols);  $\%$  默认左侧区域为1 labels(:,split_column:end)  $= 2$ $\%$  右侧区域为2   
 $\%$  使用标签图像创建两类区域的图像 leftSide_image  $=$  img rgb;  $\%$  左侧区域 leftSide_image(:,split_column:end,:)=0;  $\%$  将右侧区域设为0（黑色）
```

```matlab
right_side_image = img rgb; %右侧区域 right_side_image(:, 1:split_column-1, :) = 0; %将左侧区域设为0（黑色）  
%显示原始图像和分割后的图像 figure; subplot(1,3,1); imshow(imgrgb); title('原始图像'); subplot(1,3,2); imshow(left_side_image); title('左侧区域（磨损区域）'); subplot(1,3,3); imshow(right_side_image); title('右侧区域（翻新区域）');   
2.7最小二乘法寻找磨损系数  $\%$  假设的已知数据：总磨损体积、力和时间 V_total = [2362645, 2256789, 2187654, 2384567];  $\%$  假设的总磨损体积 (mm?), 多个数据 F = 800;  $\%$  假设的接触力(N) d = 0.1/100;  $\%$  假设的摩擦位移(cm转m) T = 51*365*1817;  $\%$  次  $\%$  磨损模型：V=k*F*d*t，其中t是时间（次）  $\%$  我们需要拟合的参数是k，即磨损系数  $\%$  反向拟合函数 wear_model = @(k,t) k*F*d*t;  $\%$  定义磨损模型  $\%$  设置初始猜测的磨损系数 k0 = 0.0001;  $\%$  初始猜测值  $\%$  目标函数：最小化总残差 objective_function = @(k) sum(abs(V_total - wear_model(k,T));  $\%$  计算所有 V_total 的残差和  $\%$  使用最小二乘法进行拟合，找到最小的总残差 k_optimal = fminsearch(objective_function, k0);  $\%$  输出拟合后的最优磨损系数 fprintf('最优磨损系数 k=%.6f mm^2/(N·m)\n', k_optimal);
```

# 2.8光滑度计算

% 读取图像
img = imread('chang.png'); % 将 'image_path.jpg' 替换为你的图像路径

$\%$  将图像转换为灰度图像（如果是彩色图像）  
if size(img, 3) == 3  
img = rgb2gray(img);  
end

$\%$  将图像转换为双精度格式，以便于处理  $\mathrm{img} = \mathrm{double}(\mathrm{img})$

$\%$  使用Sobel算子计算图像的梯度[grad_x,grad_y]  $=$  gradient(img);

$\%$  计算梯度的幅值gradMagnitude  $=$  sqrt(grad_x.^2+grad_y.^2);

$\%$  可视化梯度幅值（即图像的光滑性）  
figure;  
imshow(gradmagnitude, []);  
%\title('Gradient Magnitude (Smoothness Measure)');

$\%$  计算图像的平滑性（低梯度表示光滑）smoothness = mean(gradmagnitude(:));  $\%$  平均梯度幅值可以作为光滑性度量

% 输出光滑性值
disp(['Average Gradient Magnitude (Smoothness): ', num2str(smoothness)'));