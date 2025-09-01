'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Eye, EyeOff, Mail, Lock, User, AlertCircle, CheckCircle, Shield } from 'lucide-react';
import { api, type UserCreate, type PasswordStrengthResult } from '@/lib/api';

interface RegisterFormProps {
  onSuccess?: () => void;
  redirectTo?: string;
}

export default function RegisterForm({ onSuccess, redirectTo = '/auth/login' }: RegisterFormProps) {
  const router = useRouter();
  const [formData, setFormData] = useState<UserCreate>({
    email: '',
    password: '',
    name: '',
    role: 'viewer',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [passwordStrength, setPasswordStrength] = useState<PasswordStrengthResult | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    setSuccess('');

    try {
      // 회원가입 요청
      const user = await api.auth.register(formData);
      
      console.log('회원가입 성공:', user);
      
      setSuccess('회원가입이 완료되었습니다. 로그인해주세요.');
      
      // 성공 콜백 실행
      if (onSuccess) {
        onSuccess();
      }
      
      // 3초 후 로그인 페이지로 리다이렉트
      setTimeout(() => {
        router.push(redirectTo);
      }, 3000);
      
    } catch (err: any) {
      console.error('회원가입 오류:', err);
      
      if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else if (err.response?.status === 400) {
        setError('입력 정보를 확인해주세요.');
      } else {
        setError('회원가입 중 오류가 발생했습니다. 다시 시도해주세요.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleInputChange = async (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    
    // 입력 시 에러 메시지 초기화
    if (error) {
      setError('');
    }

    // 비밀번호 강도 실시간 체크
    if (name === 'password' && value) {
      try {
        const strength = await api.auth.checkPasswordStrength(value);
        setPasswordStrength(strength);
      } catch (err) {
        console.error('비밀번호 강도 체크 오류:', err);
      }
    } else if (name === 'password' && !value) {
      setPasswordStrength(null);
    }
  };

  const getPasswordStrengthColor = (score: number) => {
    if (score <= 1) return 'text-danger-600';
    if (score <= 3) return 'text-warning-600';
    return 'text-success-600';
  };

  const getPasswordStrengthText = (score: number) => {
    if (score <= 1) return '매우 약함';
    if (score <= 2) return '약함';
    if (score <= 3) return '보통';
    if (score <= 4) return '강함';
    return '매우 강함';
  };

  return (
    <div className="w-full max-w-md mx-auto">
      <div className="bg-white rounded-lg shadow-lg p-8">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-gray-900">회원가입</h1>
          <p className="text-gray-600 mt-2">Alpha AI Trading System 계정을 생성하세요</p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-danger-50 border border-danger-200 rounded-lg flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-danger-600 flex-shrink-0" />
            <span className="text-danger-700 text-sm">{error}</span>
          </div>
        )}

        {success && (
          <div className="mb-6 p-4 bg-success-50 border border-success-200 rounded-lg flex items-center gap-3">
            <CheckCircle className="h-5 w-5 text-success-600 flex-shrink-0" />
            <span className="text-success-700 text-sm">{success}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* 이름 입력 */}
          <div>
            <label htmlFor="name" className="label">
              이름
            </label>
            <div className="relative mt-1">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <User className="h-5 w-5 text-gray-400" />
              </div>
              <input
                id="name"
                name="name"
                type="text"
                required
                className="input pl-10"
                placeholder="이름을 입력하세요"
                value={formData.name}
                onChange={handleInputChange}
                disabled={isLoading}
              />
            </div>
          </div>

          {/* 이메일 입력 */}
          <div>
            <label htmlFor="email" className="label">
              이메일 주소
            </label>
            <div className="relative mt-1">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Mail className="h-5 w-5 text-gray-400" />
              </div>
              <input
                id="email"
                name="email"
                type="email"
                required
                className="input pl-10"
                placeholder="example@email.com"
                value={formData.email}
                onChange={handleInputChange}
                disabled={isLoading}
              />
            </div>
          </div>

          {/* 비밀번호 입력 */}
          <div>
            <label htmlFor="password" className="label">
              비밀번호
            </label>
            <div className="relative mt-1">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Lock className="h-5 w-5 text-gray-400" />
              </div>
              <input
                id="password"
                name="password"
                type={showPassword ? 'text' : 'password'}
                required
                className="input pl-10 pr-10"
                placeholder="비밀번호를 입력하세요"
                value={formData.password}
                onChange={handleInputChange}
                disabled={isLoading}
              />
              <button
                type="button"
                className="absolute inset-y-0 right-0 pr-3 flex items-center"
                onClick={() => setShowPassword(!showPassword)}
                disabled={isLoading}
              >
                {showPassword ? (
                  <EyeOff className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                ) : (
                  <Eye className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                )}
              </button>
            </div>
            
            {/* 비밀번호 강도 표시 */}
            {passwordStrength && (
              <div className="mt-2">
                <div className="flex items-center gap-2">
                  <div className="flex-1 bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full transition-all duration-300 ${
                        passwordStrength.score <= 1 ? 'bg-danger-500 w-1/5' :
                        passwordStrength.score <= 2 ? 'bg-warning-500 w-2/5' :
                        passwordStrength.score <= 3 ? 'bg-warning-500 w-3/5' :
                        passwordStrength.score <= 4 ? 'bg-success-500 w-4/5' :
                        'bg-success-500 w-full'
                      }`}
                    />
                  </div>
                  <span className={`text-xs font-medium ${getPasswordStrengthColor(passwordStrength.score)}`}>
                    {getPasswordStrengthText(passwordStrength.score)}
                  </span>
                </div>
                
                {passwordStrength.errors.length > 0 && (
                  <ul className="mt-1 text-xs text-gray-600 space-y-1">
                    {passwordStrength.errors.map((error, index) => (
                      <li key={index} className="flex items-center gap-1">
                        <span className="text-danger-500">•</span>
                        {error}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>

          {/* 역할 선택 */}
          <div>
            <label htmlFor="role" className="label">
              역할
            </label>
            <div className="relative mt-1">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Shield className="h-5 w-5 text-gray-400" />
              </div>
              <select
                id="role"
                name="role"
                className="select pl-10"
                value={formData.role}
                onChange={handleInputChange}
                disabled={isLoading}
              >
                <option value="viewer">뷰어 (조회만 가능)</option>
                <option value="trader">트레이더 (거래 가능)</option>
                <option value="admin">관리자 (모든 권한)</option>
              </select>
            </div>
          </div>

          {/* 회원가입 버튼 */}
          <button
            type="submit"
            disabled={
              isLoading || 
              !formData.email || 
              !formData.password || 
              !formData.name ||
              (passwordStrength && !passwordStrength.valid)
            }
            className="btn btn-primary w-full"
          >
            {isLoading ? (
              <div className="flex items-center justify-center gap-2">
                <div className="spinner"></div>
                <span>회원가입 중...</span>
              </div>
            ) : (
              '회원가입'
            )}
          </button>
        </form>

        {/* 추가 링크 */}
        <div className="mt-6 text-center text-sm text-gray-600">
          <p>
            이미 계정이 있으신가요?{' '}
            <button
              type="button"
              className="text-primary-600 hover:text-primary-500 font-medium"
              onClick={() => router.push('/auth/login')}
            >
              로그인
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
