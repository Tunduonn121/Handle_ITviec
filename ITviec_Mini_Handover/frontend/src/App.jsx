import { useState } from 'react'
import { useGapAnalysis } from './hooks/useGapAnalysis'

function App() {
  const [jdText, setJdText] = useState('')
  const [cvText, setCvText] = useState('')
  
  // Trạng thái lưu trữ các skill đã được User chỉnh sửa level
  const [userVerifiedSkills, setUserVerifiedSkills] = useState({})
  // Biến quản lý Màn hình hiện tại (1: Input, 2: Assessment, 3: Loading, 4: Result)
  const [extractedJdData, setExtractedJdData] = useState(null)
  const [currentStep, setCurrentStep] = useState(1)

  const { extractCv, isExtracting, extractJd, isExtractingJd, startAnalysis, isSubmitting, pollingStatus, resultData } = useGapAnalysis()

  // SỬA HÀM NÀY: Dùng Promise.all để chạy song song và chờ cả 2 hoàn tất
  const handleExtract = async () => {
    if (!cvText || !jdText) {
      alert("Sếp ơi, dán đủ cả JD và CV vào nhé!")
      return
    }

    try {
      // Gọi cả 2 API cùng một lúc và chờ kết quả
      const [jdData, cvData] = await Promise.all([
        extractJd(jdText),
        extractCv(cvText)
      ]);

      // Chỉ khi CẢ 2 đều thành công thì mới cập nhật State và chuyển trang
      setExtractedJdData(jdData);
      setUserVerifiedSkills(cvData); 
      setCurrentStep(2); 

    } catch (error) {
      // Nếu 1 trong 2 API bị lỗi, Promise.all sẽ nhảy vào đây
      console.error("Lỗi khi bóc tách dữ liệu:", error);
      alert("Có lỗi xảy ra trong quá trình AI phân tích. Vui lòng thử lại!");
    }
  }

  // SỬA HÀM NÀY: Truyền cái JD đã bóc ngầm xuống
  const handleStartAnalysis = () => {
    setCurrentStep(3) 
    startAnalysis({ jdText, cvText, verifiedSkills: userVerifiedSkills, preExtractedJd: extractedJdData })
  }

  // --- RENDERING TỪNG MÀN HÌNH ---

  // MÀN HÌNH 4: KẾT QUẢ (DASHBOARD)
  if (pollingStatus === 'completed' && resultData) {
    const { cv_skills, jd_skills, gap, combo_courses, regular_courses } = resultData;

    return (
      <div className="min-h-screen bg-slate-50 p-8 font-sans">
        <div className="max-w-7xl mx-auto">
          
          {/* HEADER DASHBOARD */}
          <div className="flex justify-between items-center mb-8">
            <div>
              <h1 className="text-3xl font-bold text-slate-800 tracking-tight">📊 Báo cáo Năng lực & Lộ trình</h1>
              <p className="text-slate-500 mt-1">Hệ thống AI đã hoàn tất phân tích đối chiếu kỹ năng.</p>
            </div>
            <button onClick={() => window.location.reload()} className="px-6 py-2 bg-slate-800 text-white font-bold rounded-lg hover:bg-blue-600 transition shadow-md">
              <i className="fa-solid fa-rotate-right mr-2"></i> Phân tích CV Mới
            </button>
          </div>

          {/* KHỐI 1: SO SÁNH 3 CỘT (CV - GAP - JD) */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
            
            {/* Cột 1: CV */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
              <h3 className="text-lg font-bold text-blue-600 mb-4 flex items-center border-b pb-2">
                <i className="fa-regular fa-file-lines mr-2"></i> Kỹ năng Ứng viên (CV)
              </h3>
              <div className="space-y-3">
                {Object.entries(cv_skills || {}).map(([skill, data]) => (
                  <div key={skill} className="flex justify-between items-center bg-blue-50/50 p-2 rounded-lg border border-blue-100">
                    <span className="font-semibold text-slate-700">{skill}</span>
                    <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs font-bold rounded">Lv {data.level}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Cột 2: GAP (Khoảng trống) */}
            <div className="bg-orange-50/30 p-6 rounded-2xl border border-orange-200 shadow-sm relative overflow-hidden">
              <div className="absolute top-0 right-0 bg-orange-500 text-white text-[10px] font-bold px-3 py-1 rounded-bl-lg">CẦN HỌC THÊM</div>
              <h3 className="text-lg font-bold text-orange-600 mb-4 flex items-center border-b border-orange-200 pb-2">
                <i className="fa-solid fa-triangle-exclamation mr-2"></i> Khoảng trống (Gap)
              </h3>
              <div className="space-y-3">
                {Object.entries(gap || {}).map(([skill, gapInfo]) => {
                  
                  // 🔥 THUẬT TOÁN BỌC THÉP: Xử lý cả 2 trường hợp Array và Object
                  const isOldFormat = Array.isArray(gapInfo);
                  const targetLevel = isOldFormat ? gapInfo[gapInfo.length - 1] : (gapInfo.level_required || '?');
                  const missingLevels = isOldFormat ? gapInfo.join(', ') : gapInfo.missing_levels?.join(', ');
                  const recText = !isOldFormat && gapInfo.recommendation ? gapInfo.recommendation : `Cần học thêm Level ${missingLevels}`;

                  return (
                    <div key={skill} className="flex flex-col bg-orange-100/50 p-3 rounded-lg border border-orange-200">
                      <div className="flex justify-between items-center mb-1">
                        <span className="font-bold text-orange-800">{skill}</span>
                        <span className="text-xs font-bold text-orange-600 bg-orange-200 px-2 py-1 rounded">
                          Mục tiêu Lv {targetLevel}
                        </span>
                      </div>
                      
                      <div className="mt-1 border-t border-orange-200/50 pt-1">
                        <p className="text-sm text-slate-700 italic">
                          💡 {recText}
                        </p>
                      </div>
                    </div>
                  );
                })}
                
                {(!gap || Object.keys(gap).length === 0) && (
                  <div className="text-center text-green-600 font-bold py-4">🎉 Tuyệt vời! Bạn cover 100% JD!</div>
                )}
              </div>
            </div>

            {/* Cột 3: JD */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
              <h3 className="text-lg font-bold text-purple-600 mb-4 flex items-center border-b pb-2">
                <i className="fa-solid fa-bullseye mr-2"></i> Yêu cầu Công việc (JD)
              </h3>
              <div className="space-y-3 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
                {Object.entries(jd_skills || {}).map(([skill, data]) => (
                  <div key={skill} className="flex flex-col bg-purple-50/50 p-2 rounded-lg border border-purple-100">
                    <div className="flex justify-between items-center">
                      <span className="font-semibold text-slate-700 text-sm">{skill}</span>
                      <span className="px-2 py-1 bg-purple-100 text-purple-700 text-xs font-bold rounded">Lv {data.level}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

          </div>

          {/* KHỐI 2: LỘ TRÌNH KHÓA HỌC */}
          <div className="space-y-8">
            
            {/* 2.1 KHU VỰC VIP: KHÓA HỌC COMBO (HỌC 1 ĐƯỢC NHIỀU) */}
            {combo_courses && combo_courses.length > 0 && (
              <div className="bg-gradient-to-br from-yellow-50 to-orange-50 p-8 rounded-2xl border-2 border-yellow-300 shadow-md relative overflow-hidden">
                <div className="absolute top-0 right-0 bg-yellow-400 text-yellow-900 text-xs font-bold px-4 py-1 rounded-bl-xl shadow-sm">AI ĐỀ XUẤT CAO NHẤT</div>
                <h2 className="text-2xl font-bold text-yellow-800 mb-6 flex items-center">
                  <i className="fa-solid fa-bolt text-yellow-500 mr-3"></i> Lộ trình Rút gọn (Combo Khóa học)
                </h2>
                <p className="text-sm text-yellow-700 mb-6 italic">Các khóa học dưới đây bao phủ nhiều kỹ năng thiếu hụt cùng lúc, giúp bạn tiết kiệm tối đa thời gian học.</p>
                
                <div className="space-y-6">
                  {combo_courses.map((course, index) => (
                    <div key={`combo-${index}`} className="bg-white p-6 rounded-xl border border-yellow-200 shadow-sm hover:shadow-md transition">
                      <div className="flex justify-between items-start mb-3">
                        <h3 className="text-xl font-bold text-slate-800">{course.title}</h3>
                        <span className="px-3 py-1 bg-yellow-100 text-yellow-800 font-bold text-sm rounded-full border border-yellow-300">Phù hợp: {course.relevance_score}/100</span>
                      </div>
                      
                      <div className="mb-4">
                        <span className="text-sm font-semibold text-slate-500 mr-2">Kỹ năng đạt được:</span>
                        <div className="flex flex-wrap gap-2 mt-2">
                          {course.target_skills.map(ts => (
                            <span key={ts} className="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs font-bold rounded">{ts}</span>
                          ))}
                        </div>
                      </div>
                      
                      <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-100 mb-4">
                        <p className="text-sm text-yellow-900"><i className="fa-solid fa-robot mr-2"></i> <strong>Lý do gộp: </strong> <br/> {course.reasoning.split(' | ').map((rs, i) => <span key={i} className="block mt-1">- {rs}</span>)}</p>
                      </div>

                      <div className="text-right">
                        <a href={course.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center px-5 py-2 bg-yellow-500 text-white font-bold text-sm rounded-lg hover:bg-yellow-600 transition shadow-sm">
                          Đến khóa Combo <i className="fa-solid fa-arrow-up-right-from-square ml-2"></i>
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 2.2 KHU VỰC REGULAR: LỘ TRÌNH TỪNG BƯỚC ĐÚNG THỨ TỰ */}
            <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm">
              <h2 className="text-2xl font-bold text-slate-800 mb-6 flex items-center">
                <i className="fa-solid fa-shoe-prints text-blue-500 mr-3"></i> Lộ trình Từng bước (Theo thứ tự Gap)
              </h2>
              
              <div className="space-y-6 border-l-4 border-slate-100 ml-4 pl-8">
                {(regular_courses || []).map((course, index) => (
                  <div key={`regular-${index}`} className="relative">
                    {/* Dấu chấm tròn của Timeline */}
                    <span className="absolute -left-[43px] top-2 flex items-center justify-center w-8 h-8 bg-white border-4 border-blue-400 rounded-full text-xs font-bold text-slate-700">
                      {index + 1}
                    </span>
                    
                    <div className="bg-slate-50 p-6 rounded-xl border border-slate-200 hover:shadow-md transition">
                      <div className="flex justify-between items-start mb-3">
                        <h3 className="text-xl font-bold text-slate-800">{course.title}</h3>
                        <span className="px-3 py-1 bg-blue-50 text-blue-700 font-bold text-sm rounded-full border border-blue-200">Độ phù hợp: {course.relevance_score}/100</span>
                      </div>
                      
                      <div className="mb-4">
                        <span className="text-sm font-semibold text-slate-500 mr-2">Kỹ năng đạt được:</span>
                        <div className="flex flex-wrap gap-2 mt-2">
                          {course.target_skills.map(ts => (
                            <span key={ts} className="px-2 py-1 bg-slate-200 text-slate-700 text-xs font-semibold rounded">{ts}</span>
                          ))}
                        </div>
                      </div>
                      
                      <div className="bg-blue-50 p-4 rounded-lg border border-blue-100 mb-4">
                        <p className="text-sm text-blue-800"><i className="fa-solid fa-robot mr-2"></i> <strong>AI Đánh giá: </strong> {course.reasoning}</p>
                      </div>

                      <div className="text-right">
                        <a href={course.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center px-5 py-2 bg-slate-800 text-white font-bold text-sm rounded-lg hover:bg-slate-700 transition shadow-sm">
                          Đến khóa học <i className="fa-solid fa-arrow-up-right-from-square ml-2"></i>
                        </a>
                      </div>

                    </div>
                  </div>
                ))}
                
                {(!regular_courses || regular_courses.length === 0) && (
                  <p className="text-slate-500 italic">Mọi kỹ năng thiếu hụt đã được bao phủ bởi các khóa Combo ở trên!</p>
                )}
              </div>
            </div>

          </div>

        </div>
      </div>
    )
  }

  // MÀN HÌNH 3: LOADING CHỜ AI PHÂN TÍCH GAP
  if (currentStep === 3 || isSubmitting || pollingStatus === 'processing') {
    return (
      <div className="min-h-screen bg-slate-900 text-slate-300 p-8 flex flex-col items-center justify-center font-sans">
        
        <div className="max-w-5xl w-full bg-slate-800 rounded-3xl shadow-2xl border border-slate-700 p-8 mb-10 relative overflow-hidden">
          
          {/* Tia sáng chạy ngang mờ mờ cho có vẻ nguy hiểm */}
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-blue-500 to-transparent animate-pulse"></div>

          <h2 className="text-2xl font-bold text-center text-white mb-8 flex justify-center items-center">
            <i className="fa-solid fa-microchip animate-pulse text-blue-400 mr-3"></i> 
            Hệ thống đang đối chiếu Dữ liệu
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* CỘT TRÁI: CV SKILLS (Đã có data từ bước 2) */}
            <div className="bg-slate-900/80 p-6 rounded-2xl border border-slate-700">
              <h3 className="text-lg font-bold text-blue-400 mb-5 border-b border-slate-700 pb-3 flex items-center">
                <i className="fa-regular fa-file-lines mr-2"></i> Năng lực Ứng viên (CV)
              </h3>
              <div className="space-y-3 max-h-[250px] overflow-y-auto pr-2 custom-scrollbar">
                {Object.entries(userVerifiedSkills).map(([skill, data]) => (
                  <div key={skill} className="flex justify-between items-center bg-slate-800 p-3 rounded-xl border border-slate-700/50">
                    <span className="font-semibold text-slate-200">{skill}</span>
                    <span className="px-3 py-1 bg-blue-900/50 text-blue-300 rounded-lg text-sm font-bold border border-blue-800/50">
                      Level {data.level}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* CỘT PHẢI: JD SKILLS */}
            <div className="bg-slate-900/80 p-6 rounded-2xl border border-slate-700">
              <h3 className="text-lg font-bold text-purple-400 mb-5 border-b border-slate-700 pb-3 flex items-center">
                <i className="fa-solid fa-bullseye mr-2"></i> Yêu cầu Công việc (JD)
              </h3>
              <div className="space-y-3 max-h-[250px] overflow-y-auto pr-2 custom-scrollbar">
                
                {/* HIỂN THỊ DỮ LIỆU THẬT NẾU ĐÃ BÓC NGẦM XONG */}
                {extractedJdData ? (
                  Object.entries(extractedJdData).map(([skill, data]) => (
                    <div key={skill} className="flex justify-between items-center bg-slate-800 p-3 rounded-xl border border-slate-700/50">
                      <span className="font-semibold text-slate-200">{skill}</span>
                      <span className="px-3 py-1 bg-purple-900/50 text-purple-300 rounded-lg text-sm font-bold border border-purple-800/50">
                        Yêu cầu Lv {data.level}
                      </span>
                    </div>
                  ))
                ) : (
                  /* NẾU USER THAO TÁC QUÁ NHANH, JD CHƯA KỊP BÓC XONG THÌ HIỆN SKELETON */
                  <div className="space-y-4">
                    <div className="text-sm text-purple-300/70 italic mb-2 animate-pulse">Đang hoàn tất bóc tách JD...</div>
                    {[1, 2, 3, 4].map(i => (
                      <div key={i} className="flex justify-between items-center bg-slate-800/50 p-3 rounded-xl border border-slate-700/30 animate-pulse">
                        <div className={`h-5 bg-slate-700 rounded-md w-${i % 2 === 0 ? '1/2' : '2/3'}`}></div>
                        <div className="h-6 bg-slate-700 rounded-md w-16"></div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* PHẦN DƯỚI: SKILL GAP (Hiệu ứng đang tính toán) */}
          <div className="mt-8 bg-slate-900/80 p-6 rounded-2xl border border-slate-700 text-center">
             <h3 className="text-lg font-bold text-orange-400 mb-4 flex items-center justify-center">
               <i className="fa-solid fa-magnifying-glass-chart mr-2 animate-bounce"></i> Phát hiện Skill Gap (Kỹ năng thiếu hụt)
             </h3>
             <div className="flex justify-center gap-4 flex-wrap">
                <div className="w-24 h-10 bg-slate-800 rounded-xl animate-pulse border border-slate-700"></div>
                <div className="w-32 h-10 bg-slate-800 rounded-xl animate-pulse border border-slate-700"></div>
                <div className="w-28 h-10 bg-slate-800 rounded-xl animate-pulse border border-slate-700"></div>
                <div className="w-20 h-10 bg-slate-800 rounded-xl animate-pulse border border-slate-700"></div>
             </div>
             <p className="text-sm text-slate-500 mt-4 italic">Đang dùng thuật toán so khớp Level để tìm ra khoảng trống năng lực...</p>
          </div>

        </div>

        {/* DÒNG TEXT GIỮ NGUYÊN THEO CHỈ ĐẠO CỦA SẾP */}
        <h1 className="text-4xl font-bold mt-2 text-blue-500 tracking-wide drop-shadow-lg">
           Đang Thiết Kế Lộ Trình...
        </h1>
        <p className="text-slate-400 mt-4 text-lg animate-pulse">
          Vui lòng chờ trong giây lát. Hệ thống đang tìm kiếm khóa học phù hợp nhất...
        </p>
      </div>
    )
  }

  // MÀN HÌNH 2: TỰ ĐÁNH GIÁ (SELF-ASSESSMENT)
  if (currentStep === 2) {
    return (
      <div className="min-h-screen bg-slate-50 p-10">
        <div className="max-w-6xl mx-auto text-center mb-10">
          <h2 className="text-3xl font-bold text-slate-800">✅ Xác nhận Năng lực Thực tế</h2>
          <p className="text-slate-500 mt-2">AI đã trích xuất các kỹ năng từ CV. Vui lòng đối chiếu với bảng tiêu chí bên phải để chọn trình độ chính xác nhất.</p>
        </div>

        {/* Layout chia 2 cột: Trái chứa Slider, Phải chứa Hướng dẫn */}
        <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-8">
          
          {/* CỘT TRÁI: DANH SÁCH SKILL (Chiếm 2/3) */}
          <div className="md:col-span-2 bg-white p-8 rounded-2xl shadow-xl border border-slate-200">
            <div className="space-y-6">
              {Object.entries(userVerifiedSkills).map(([skill, data]) => (
                <div key={skill} className="flex items-center justify-between p-4 bg-slate-50 rounded-xl border border-slate-100 hover:border-blue-200 transition-colors">
                  <div className="w-1/3">
                    <span className="font-bold text-lg text-slate-700 bg-blue-100 text-blue-700 px-3 py-1 rounded-md">{skill}</span>
                  </div>
                  <div className="w-2/3 flex items-center gap-6">
                    <input 
                      type="range" min="1" max="3" step="1" 
                      value={data.level} 
                      onChange={(e) => handleLevelChange(skill, e.target.value)}
                      className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                    />
                    <div className="w-32 text-right">
                      {data.level == 1 && <span className="font-bold text-blue-600">Level 1</span>}
                      {data.level == 2 && <span className="font-bold text-green-600">Level 2</span>}
                      {data.level == 3 && <span className="font-bold text-purple-600">Level 3</span>}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-10 text-center flex justify-center gap-4">
              <button onClick={() => setCurrentStep(1)} className="px-8 py-3 rounded-xl font-bold bg-slate-200 text-slate-700 hover:bg-slate-300 transition-all">Quay lại sửa CV</button>
              <button onClick={handleStartAnalysis} className="px-8 py-3 rounded-xl font-bold bg-blue-600 text-white shadow-lg hover:bg-blue-700 transition-all">Xác nhận & Phân tích JD ✨</button>
            </div>
          </div>

          {/* CỘT PHẢI: BẢNG HƯỚNG DẪN LEVEL (Chiếm 1/3) */}
          <div className="md:col-span-1">
            <div className="bg-blue-50 p-6 rounded-2xl border border-blue-100 shadow-sm sticky top-10">
              <h3 className="text-xl font-bold text-blue-800 mb-4 flex items-center">
                <i className="fa-solid fa-circle-info mr-2"></i> Tiêu chí Đánh giá
              </h3>
              
              <div className="space-y-4">
                {/* Level 1 Card */}
                <div className="bg-white p-4 rounded-xl border border-blue-200 shadow-sm">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="bg-blue-600 text-white text-xs font-bold px-2 py-1 rounded">Lv 1</span>
                    <span className="font-bold text-blue-700">Beginner (Tập sự)</span>
                  </div>
                  <p className="text-sm text-slate-600 leading-relaxed">
                    Nắm vững lý thuyết cơ bản và cú pháp. Có thể hoàn thành các bài tập nhỏ hoặc đồ án môn học dưới sự hướng dẫn.
                  </p>
                </div>

                {/* Level 2 Card */}
                <div className="bg-white p-4 rounded-xl border border-green-200 shadow-sm">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="bg-green-600 text-white text-xs font-bold px-2 py-1 rounded">Lv 2</span>
                    <span className="font-bold text-green-700">Intermediate (Thực chiến)</span>
                  </div>
                  <p className="text-sm text-slate-600 leading-relaxed">
                    Đã có kinh nghiệm làm dự án thực tế. Biết sử dụng framework/thư viện, có khả năng tự tra cứu tài liệu và fix bug độc lập.
                  </p>
                </div>

                {/* Level 3 Card */}
                <div className="bg-white p-4 rounded-xl border border-purple-200 shadow-sm">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="bg-purple-600 text-white text-xs font-bold px-2 py-1 rounded">Lv 3</span>
                    <span className="font-bold text-purple-700">Advanced (Chuyên sâu)</span>
                  </div>
                  <p className="text-sm text-slate-600 leading-relaxed">
                    Hiểu sâu bản chất và kiến trúc hệ thống. Có khả năng tối ưu hiệu năng, bảo mật và thiết kế giải pháp cho bài toán phức tạp.
                  </p>
                </div>
              </div>
              
            </div>
          </div>

        </div>
      </div>
    )
  }

  // MÀN HÌNH 1: NHẬP DỮ LIỆU (CÓ NÚT LOADING)
  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <h1 className="text-4xl font-bold text-center mb-10 text-slate-800">IT Skill Gap <span className="text-blue-600">SaaS</span></h1>
      
      <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <h2 className="text-xl font-bold mb-4 text-slate-700">📋 Job Description (Dán JD vào đây)</h2>
          <textarea className="w-full h-[400px] p-4 border rounded-xl outline-none bg-slate-50" value={jdText} onChange={(e) => setJdText(e.target.value)} />
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 relative">
          <h2 className="text-xl font-bold mb-4 text-slate-700">📄 Dán CV Ứng Viên</h2>
          <textarea className="w-full h-[400px] p-4 border rounded-xl outline-none bg-slate-50" value={cvText} onChange={(e) => setCvText(e.target.value)} />
          
          {/* Lớp mờ khi AI đang bóc tách */}
          {/* SỬA Ở ĐÂY: Check cả isExtracting và isExtractingJd */}
          {(isExtracting || isExtractingJd) && (
             <div className="absolute inset-0 bg-white/80 flex items-center justify-center rounded-2xl backdrop-blur-sm">
               <div className="text-2xl font-bold text-blue-600 animate-pulse">🤖 Đang quét dữ liệu...</div>
             </div>
          )}
        </div>
      </div>

      <div className="text-center mt-10">
        {/* SỬA Ở ĐÂY: Khóa nút khi 1 trong 2 thằng đang chạy */}
        <button onClick={handleExtract} disabled={isExtracting || isExtractingJd} className="bg-slate-900 hover:bg-blue-600 text-white px-10 py-4 rounded-full font-bold text-lg shadow-xl disabled:bg-slate-400">
          Bước 1: Trích xuất Dữ liệu 🚀
        </button>
      </div>
    </div>
  )
}

export default App